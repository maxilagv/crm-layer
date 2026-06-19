from django.db import IntegrityError, transaction
from django.utils import timezone

from crm.contacts.constants import ContactSource
from crm.contacts.services import ContactResolver
from crm.conversations.constants import (
    ACTIVE_STATUSES,
    Channel,
    MessageDirection,
    MessageStatus,
)
from crm.conversations.models import Conversation, Message, MessageAttachment
from crm.conversations.normalizers import clean_body, normalize_text
from crm.conversations.router import ConversationRouter
from crm.core.services.outbox import create_outbox_event
from crm.organizations.models import Organization
from crm.whatsapp.domain import events, policies
from crm.whatsapp.domain.enums import (
    InboundMessageStatus,
    MediaReferenceStatus,
    WhatsAppMessageType,
)
from crm.whatsapp.models import (
    WhatsAppInboundMessage,
    WhatsAppMediaReference,
    WhatsAppPhoneNumber,
    WhatsAppWebhookEvent,
)
from crm.whatsapp.services.payload_parser import (
    extract_media_descriptor,
    extract_message_body,
    iter_changes,
    normalize_message_type,
    parse_meta_timestamp,
)


def _phone_for_contact(wa_id: str, from_phone: str) -> str:
    raw = wa_id or from_phone
    return raw if str(raw).startswith("+") else f"+{raw}"


def _resolve_conversation(*, organization_id, contact) -> Conversation:
    conversation = (
        Conversation.objects.filter(
            organization_id=organization_id,
            contact=contact,
            channel=Channel.WHATSAPP,
            status__in=ACTIVE_STATUSES,
        )
        .order_by("-last_message_at", "-created_at")
        .first()
    )
    if conversation is not None:
        return conversation
    return Conversation.objects.create(
        organization_id=organization_id,
        contact=contact,
        channel=Channel.WHATSAPP,
        mode=ConversationRouter.route(contact),
    )


def _profile_name(value: dict, wa_id: str) -> str:
    for profile in value.get("contacts") or []:
        if str(profile.get("wa_id") or "") == wa_id:
            return str((profile.get("profile") or {}).get("name") or "")
    return ""


def _create_media_reference(
    *,
    organization_id,
    webhook_event,
    inbound_message,
    crm_message,
    descriptor,
    message_type,
) -> WhatsAppMediaReference | None:
    attachment = MessageAttachment.objects.create(
        organization_id=organization_id,
        message=crm_message,
        external_media_id=descriptor["external_media_id"],
        mime_type=descriptor["mime_type"],
        file_name=descriptor["file_name"],
    )
    try:
        media_reference, created = WhatsAppMediaReference.objects.get_or_create(
            organization_id=organization_id,
            external_media_id=descriptor["external_media_id"],
            defaults={
                "webhook_event": webhook_event,
                "inbound_message": inbound_message,
                "crm_message": crm_message,
                "crm_attachment": attachment,
                "media_type": message_type,
                "mime_type": descriptor["mime_type"],
                "sha256": descriptor["sha256"],
                "file_name": descriptor["file_name"],
                "status": MediaReferenceStatus.QUEUED,
            },
        )
    except IntegrityError:
        media_reference = WhatsAppMediaReference.objects.filter(
            organization_id=organization_id,
            external_media_id=descriptor["external_media_id"],
        ).first()
        created = False
    if created:
        create_outbox_event(
            event_type=events.MEDIA_REFERENCE_CREATED,
            organization_id=organization_id,
            payload={
                "media_reference_id": str(media_reference.id),
                "external_media_id": media_reference.external_media_id,
            },
        )
        from crm.whatsapp.tasks import download_media

        transaction.on_commit(lambda: download_media.delay(str(media_reference.id)))
    return media_reference


@transaction.atomic
def handle_inbound_messages(webhook_event: WhatsAppWebhookEvent) -> int:
    processed = 0
    for change in iter_changes(webhook_event.raw_payload):
        value = change.value
        phone_number_id = str((value.get("metadata") or {}).get("phone_number_id") or "")
        phone_number = (
            WhatsAppPhoneNumber.objects.select_related("business_account")
            .filter(phone_number_id=phone_number_id)
            .first()
        )
        if phone_number is None:
            continue
        organization = Organization.objects.get(id=phone_number.organization_id)

        for message in value.get("messages") or []:
            external_message_id = str(message.get("id") or "")
            if not external_message_id:
                continue
            existing = WhatsAppInboundMessage.objects.filter(
                organization_id=organization.id,
                external_message_id=external_message_id,
            ).first()
            if existing is not None:
                processed += 1
                continue

            wa_id = str(message.get("from") or "")
            from_phone = _phone_for_contact(wa_id, wa_id)
            message_type = normalize_message_type(message)
            body = clean_body(extract_message_body(message, message_type))
            received_at = parse_meta_timestamp(message.get("timestamp")) or timezone.now()
            profile_name = _profile_name(value, wa_id)

            resolved = ContactResolver.resolve_by_phone(
                organization=organization,
                raw_phone=from_phone,
                create=True,
                source=ContactSource.WHATSAPP,
                is_whatsapp=True,
            )
            contact = resolved.contact
            if contact is None:
                continue
            if profile_name and contact.display_name == from_phone:
                contact.display_name = profile_name
                contact.save(update_fields=["display_name", "updated_at"])

            conversation = _resolve_conversation(organization_id=organization.id, contact=contact)
            crm_type = policies.crm_message_type(message_type)
            crm_status = (
                MessageStatus.IGNORED
                if message_type == WhatsAppMessageType.UNSUPPORTED.value
                else MessageStatus.PROCESSED
            )
            crm_message, _created = Message.objects.get_or_create(
                organization_id=organization.id,
                external_message_id=external_message_id,
                defaults={
                    "conversation": conversation,
                    "contact": contact,
                    "direction": MessageDirection.INBOUND,
                    "message_type": crm_type,
                    "body": body,
                    "normalized_text": normalize_text(body),
                    "external_timestamp": received_at,
                    "status": crm_status,
                    "raw_payload": {
                        "provider": "whatsapp",
                        "external_message_id": external_message_id,
                        "message_type": message_type,
                    },
                },
            )
            inbound = WhatsAppInboundMessage.objects.create(
                organization_id=organization.id,
                webhook_event=webhook_event,
                conversation=conversation,
                contact=contact,
                crm_message=crm_message,
                phone_number=phone_number,
                from_phone_e164=from_phone,
                wa_id=wa_id,
                external_message_id=external_message_id,
                message_type=message_type,
                body=body,
                raw_message=message,
                received_at=received_at,
                processed_at=timezone.now(),
                status=InboundMessageStatus.PROCESSED,
            )

            media_descriptor = extract_media_descriptor(message, message_type)
            if media_descriptor is not None:
                _create_media_reference(
                    organization_id=organization.id,
                    webhook_event=webhook_event,
                    inbound_message=inbound,
                    crm_message=crm_message,
                    descriptor=media_descriptor,
                    message_type=message_type,
                )

            now = timezone.now()
            conversation.last_message_at = received_at
            conversation.last_inbound_at = received_at
            conversation.mode = ConversationRouter.route(contact, conversation)
            conversation.save(
                update_fields=["last_message_at", "last_inbound_at", "mode", "updated_at"]
            )
            create_outbox_event(
                event_type="conversation.message_received.v1",
                organization_id=organization.id,
                payload={
                    "conversation_id": str(conversation.id),
                    "message_id": str(crm_message.id),
                    "contact_id": str(contact.id),
                    "external_message_id": external_message_id,
                    "received_at": received_at.isoformat(),
                    "created_at": now.isoformat(),
                },
            )
            create_outbox_event(
                event_type=events.INBOUND_MESSAGE_RECEIVED,
                organization_id=organization.id,
                payload={
                    "whatsapp_inbound_message_id": str(inbound.id),
                    "external_message_id": external_message_id,
                },
            )
            processed += 1
    return processed
