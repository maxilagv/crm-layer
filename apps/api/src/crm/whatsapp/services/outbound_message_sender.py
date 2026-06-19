from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from crm.audit.services import audit_event_create
from crm.conversations.constants import Channel, MessageDirection, MessageStatus, MessageType
from crm.conversations.models import Conversation, Message
from crm.conversations.normalizers import clean_body, normalize_text
from crm.core.logging import sanitize
from crm.core.services.outbox import create_outbox_event
from crm.whatsapp.clients.meta_client import MetaAPIError, MetaClient
from crm.whatsapp.domain import events
from crm.whatsapp.domain.enums import OutboundMessageStatus, WhatsAppMessageType
from crm.whatsapp.models import WhatsAppOutboundMessage, WhatsAppPhoneNumber


@dataclass(frozen=True)
class QueueResult:
    outbound: WhatsAppOutboundMessage
    created: bool


class RetryableOutboundSendError(Exception):
    """Outbound failed after being persisted and can be retried by Celery."""


def _default_phone_number(organization_id) -> WhatsAppPhoneNumber:
    phone_number = (
        WhatsAppPhoneNumber.objects.filter(organization_id=organization_id, status="active")
        .order_by("created_at")
        .first()
    )
    if phone_number is None:
        raise ValidationError({"phone_number": "No active WhatsApp phone number configured"})
    return phone_number


def _recipient_phone(contact) -> str:
    phone = (
        contact.phones.filter(is_whatsapp=True).order_by("-is_primary", "created_at").first()
        or contact.phones.order_by("-is_primary", "created_at").first()
    )
    if phone is None:
        raise ValidationError({"contact_id": "Contact has no phone number"})
    return phone.phone_e164.lstrip("+")


def _validate_conversation_contact(organization, conversation: Conversation, contact) -> None:
    if (
        conversation.organization_id != organization.id
        or contact.organization_id != organization.id
    ):
        raise ValidationError("Conversation/contact do not belong to current organization")
    if conversation.contact_id != contact.id:
        raise ValidationError("Conversation does not belong to contact")
    if conversation.channel != Channel.WHATSAPP:
        raise ValidationError("Conversation is not a WhatsApp conversation")


@transaction.atomic
def queue_text_message(
    *,
    organization,
    conversation: Conversation,
    contact,
    body: str,
    actor=None,
    request=None,
    idempotency_key: str = "",
) -> QueueResult:
    _validate_conversation_contact(organization, conversation, contact)
    if idempotency_key:
        existing = WhatsAppOutboundMessage.objects.filter(
            organization_id=organization.id,
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            return QueueResult(outbound=existing, created=False)

    phone_number = _default_phone_number(organization.id)
    recipient_phone = _recipient_phone(contact)
    body = clean_body(body)
    if not body:
        raise ValidationError({"body": "Body is required"})
    crm_message = Message.objects.create(
        organization_id=organization.id,
        conversation=conversation,
        contact=contact,
        direction=MessageDirection.OUTBOUND,
        message_type=MessageType.TEXT,
        body=body,
        normalized_text=normalize_text(body),
        status=MessageStatus.QUEUED,
        raw_payload={"provider": "whatsapp", "message_type": "text"},
    )
    outbound = WhatsAppOutboundMessage.objects.create(
        organization_id=organization.id,
        conversation=conversation,
        contact=contact,
        crm_message=crm_message,
        phone_number=phone_number,
        message_type=WhatsAppMessageType.TEXT,
        body=body,
        recipient_phone_e164=recipient_phone,
        idempotency_key=idempotency_key,
        payload={"type": "text", "body": body},
        created_by_id=getattr(actor, "id", None),
    )
    create_outbox_event(
        event_type=events.OUTBOUND_MESSAGE_QUEUED,
        organization_id=organization.id,
        payload={"outbound_message_id": str(outbound.id)},
    )
    audit_event_create(
        event_type="whatsapp_outbound_queued",
        actor=actor,
        organization=organization,
        request=request,
        resource_type="whatsapp_outbound_message",
        resource_id=str(outbound.id),
        metadata={"message_type": "text"},
    )
    from crm.whatsapp.tasks import send_outbound_message

    transaction.on_commit(lambda: send_outbound_message.delay(str(outbound.id)))
    return QueueResult(outbound=outbound, created=True)


def send_queued_outbound_message(
    outbound_id,
    *,
    client: MetaClient | None = None,
) -> WhatsAppOutboundMessage:
    with transaction.atomic():
        outbound = (
            WhatsAppOutboundMessage.objects.select_for_update(of=("self",))
            .select_related("phone_number", "crm_message")
            .get(id=outbound_id)
        )
        if outbound.external_message_id and outbound.status in {
            OutboundMessageStatus.SENT,
            OutboundMessageStatus.DELIVERED,
            OutboundMessageStatus.READ,
        }:
            return outbound
        if outbound.status == OutboundMessageStatus.CANCELED:
            return outbound
        if outbound.status not in {OutboundMessageStatus.QUEUED, OutboundMessageStatus.FAILED}:
            return outbound

        outbound.status = OutboundMessageStatus.SENDING
        outbound.attempts += 1
        outbound.last_attempt_at = timezone.now()
        outbound.save(update_fields=["status", "attempts", "last_attempt_at", "updated_at"])

    client = client or MetaClient()
    try:
        if outbound.message_type == WhatsAppMessageType.TEMPLATE:
            response = client.send_template_message(
                phone_number_id=outbound.phone_number.phone_number_id,
                recipient_phone=outbound.recipient_phone_e164,
                template_name=outbound.template_name,
                language=outbound.payload.get("language", "es_AR"),
                components=outbound.payload.get("components") or [],
            )
        else:
            response = client.send_text_message(
                phone_number_id=outbound.phone_number.phone_number_id,
                recipient_phone=outbound.recipient_phone_e164,
                body=outbound.body,
            )
    except MetaAPIError as exc:
        with transaction.atomic():
            outbound = WhatsAppOutboundMessage.objects.select_for_update().get(id=outbound_id)
            outbound.status = OutboundMessageStatus.FAILED
            outbound.failed_at = timezone.now()
            outbound.error_code = exc.code
            outbound.error_message = str(exc)[:500]
            outbound.response_payload = sanitize(exc.response_payload)
            outbound.save(
                update_fields=[
                    "status",
                    "failed_at",
                    "error_code",
                    "error_message",
                    "response_payload",
                    "updated_at",
                ]
            )
            if outbound.crm_message_id:
                Message.objects.filter(id=outbound.crm_message_id).update(
                    status=MessageStatus.FAILED,
                    updated_at=timezone.now(),
                )
            create_outbox_event(
                event_type=events.OUTBOUND_MESSAGE_FAILED,
                organization_id=outbound.organization_id,
                payload={
                    "outbound_message_id": str(outbound.id),
                    "error_code": outbound.error_code,
                },
            )
        audit_event_create(
            event_type="whatsapp_outbound_failed",
            organization=_org_stub(outbound.organization_id),
            resource_type="whatsapp_outbound_message",
            resource_id=str(outbound.id),
            metadata={"error_code": outbound.error_code},
        )
        if exc.retryable:
            raise RetryableOutboundSendError(str(exc)) from exc
        return outbound

    with transaction.atomic():
        outbound = WhatsAppOutboundMessage.objects.select_for_update().get(id=outbound_id)
        if outbound.external_message_id:
            return outbound
        outbound.status = OutboundMessageStatus.SENT
        outbound.external_message_id = response.external_message_id
        outbound.sent_at = timezone.now()
        outbound.error_code = ""
        outbound.error_message = ""
        outbound.response_payload = sanitize(response.raw_response)
        outbound.save(
            update_fields=[
                "status",
                "external_message_id",
                "sent_at",
                "error_code",
                "error_message",
                "response_payload",
                "updated_at",
            ]
        )
        if outbound.crm_message_id:
            Message.objects.filter(id=outbound.crm_message_id).update(
                external_message_id=response.external_message_id,
                status=MessageStatus.SENT,
                updated_at=timezone.now(),
            )
        create_outbox_event(
            event_type=events.OUTBOUND_MESSAGE_SENT,
            organization_id=outbound.organization_id,
            payload={
                "outbound_message_id": str(outbound.id),
                "external_message_id": response.external_message_id,
            },
        )
    return outbound


def _org_stub(organization_id):
    class _Org:
        id = organization_id

    return _Org()
