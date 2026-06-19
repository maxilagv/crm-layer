from django.db import transaction
from rest_framework.exceptions import ValidationError

from crm.audit.services import audit_event_create
from crm.conversations.constants import MessageDirection, MessageStatus, MessageType
from crm.conversations.models import Conversation, Message
from crm.conversations.normalizers import normalize_text
from crm.whatsapp.domain.enums import OutboundMessageStatus, WhatsAppMessageType
from crm.whatsapp.models import WhatsAppOutboundMessage, WhatsAppTemplate
from crm.whatsapp.services.outbound_message_sender import (
    QueueResult,
    _default_phone_number,
    _recipient_phone,
    _validate_conversation_contact,
)


@transaction.atomic
def queue_template_message(
    *,
    organization,
    conversation: Conversation,
    contact,
    template_name: str,
    language: str,
    components: list[dict] | None = None,
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

    template = WhatsAppTemplate.objects.filter(
        organization_id=organization.id,
        name=template_name,
        language=language,
    ).first()
    if template is None:
        raise ValidationError({"template_name": "Template does not exist"})

    phone_number = _default_phone_number(organization.id)
    recipient_phone = _recipient_phone(contact)
    components = components or []
    body = f"Template: {template_name}"
    crm_message = Message.objects.create(
        organization_id=organization.id,
        conversation=conversation,
        contact=contact,
        direction=MessageDirection.OUTBOUND,
        message_type=MessageType.TEXT,
        body=body,
        normalized_text=normalize_text(body),
        status=MessageStatus.QUEUED,
        raw_payload={"provider": "whatsapp", "message_type": "template"},
    )
    outbound = WhatsAppOutboundMessage.objects.create(
        organization_id=organization.id,
        conversation=conversation,
        contact=contact,
        crm_message=crm_message,
        phone_number=phone_number,
        message_type=WhatsAppMessageType.TEMPLATE,
        template_name=template.name,
        body="",
        recipient_phone_e164=recipient_phone,
        idempotency_key=idempotency_key,
        payload={
            "type": "template",
            "template_name": template.name,
            "language": template.language,
            "components": components,
        },
        status=OutboundMessageStatus.QUEUED,
        created_by_id=getattr(actor, "id", None),
    )
    audit_event_create(
        event_type="whatsapp_template_queued",
        actor=actor,
        organization=organization,
        request=request,
        resource_type="whatsapp_outbound_message",
        resource_id=str(outbound.id),
        metadata={"template_name": template.name, "language": template.language},
    )
    from crm.whatsapp.tasks import send_outbound_message

    transaction.on_commit(lambda: send_outbound_message.delay(str(outbound.id)))
    return QueueResult(outbound=outbound, created=True)
