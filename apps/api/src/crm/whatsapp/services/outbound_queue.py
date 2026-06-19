"""Pull-based outbound queue for the local WhatsApp bridge."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from crm.audit.services import audit_event_create
from crm.contacts.constants import ContactSource, ContactType
from crm.contacts.services import ContactResolver
from crm.conversations.constants import Channel, MessageDirection, MessageStatus, MessageType
from crm.conversations.models import Message
from crm.conversations.services import ConversationResolver, MessageIngestionService
from crm.core.services.outbox import create_outbox_event
from crm.whatsapp.domain import events
from crm.whatsapp.domain.enums import BridgeOutboundStatus
from crm.whatsapp.models import OutboundMessage

MAX_DELIVERY_ATTEMPTS = 5
BACKOFF_CAP_SECONDS = 300


@dataclass(frozen=True)
class OutboundQueueResult:
    outbound: OutboundMessage
    created: bool


class WhatsAppOutboundQueueService:
    @staticmethod
    def enqueue(
        *,
        organization,
        phone: str,
        body: str,
        prospect_id=None,
        conversation=None,
        contact=None,
        available_at=None,
        idempotency_key: str = "",
        actor=None,
        request=None,
    ) -> OutboundQueueResult:
        body = (body or "").strip()
        if not phone:
            raise ValidationError({"phone": "Phone is required"})
        if not body:
            raise ValidationError({"body": "Body is required"})

        key = idempotency_key or f"bridge-outbound:{uuid.uuid4()}"
        existing = OutboundMessage.objects.filter(
            organization_id=organization.id,
            idempotency_key=key,
        ).first()
        if existing is not None:
            return OutboundQueueResult(outbound=existing, created=False)

        try:
            with transaction.atomic():
                resolved = None
                if contact is None:
                    resolved = ContactResolver.resolve_by_phone(
                        organization=organization,
                        raw_phone=phone,
                        create=True,
                        contact_type=ContactType.LEAD,
                        source=ContactSource.PROSPECTING,
                        request=request,
                    )
                    contact = resolved.contact
                if contact is None:
                    raise ValidationError({"phone": "Could not resolve contact"})
                if contact.organization_id != organization.id:
                    raise ValidationError("Contact does not belong to current organization")

                if conversation is None:
                    conversation = ConversationResolver.resolve(
                        organization=organization,
                        contact=contact,
                        channel=Channel.WHATSAPP,
                        request=request,
                    ).conversation
                if conversation is None:
                    raise ValidationError({"conversation": "Could not resolve conversation"})
                if (
                    conversation.organization_id != organization.id
                    or conversation.contact_id != contact.id
                    or conversation.channel != Channel.WHATSAPP
                ):
                    raise ValidationError("Conversation/contact mismatch")

                ingestion = MessageIngestionService.ingest(
                    organization=organization,
                    channel=Channel.WHATSAPP,
                    direction=MessageDirection.OUTBOUND,
                    contact=contact,
                    conversation=conversation,
                    message_type=MessageType.TEXT,
                    body=body,
                    status=MessageStatus.QUEUED,
                    actor=actor,
                    request=request,
                )
                outbound = OutboundMessage.objects.create(
                    organization_id=organization.id,
                    contact_phone=_phone_for_queue(resolved=resolved, fallback=phone),
                    body=body,
                    idempotency_key=key,
                    available_at=available_at or timezone.now(),
                    prospect_id=prospect_id,
                    conversation_id=conversation.id,
                    contact_id=contact.id,
                    metadata={"crm_message_id": str(ingestion.message.id)},
                    created_by_id=getattr(actor, "id", None),
                )
                create_outbox_event(
                    event_type=events.OUTBOUND_MESSAGE_QUEUED,
                    organization_id=organization.id,
                    payload={
                        "outbound_message_id": str(outbound.id),
                        "queue": "bridge",
                        "conversation_id": str(conversation.id),
                    },
                )
                audit_event_create(
                    event_type="whatsapp_bridge_outbound_queued",
                    actor=actor,
                    organization=organization,
                    request=request,
                    resource_type="whatsapp_outbound_message_queue",
                    resource_id=str(outbound.id),
                    metadata={"prospect_id": str(prospect_id or "")},
                )
                return OutboundQueueResult(outbound=outbound, created=True)
        except IntegrityError:
            existing = OutboundMessage.objects.get(
                organization_id=organization.id,
                idempotency_key=key,
            )
            return OutboundQueueResult(outbound=existing, created=False)

    @staticmethod
    @transaction.atomic
    def claim_pending(*, organization, limit: int = 20) -> list[OutboundMessage]:
        limit = max(1, min(int(limit or 20), 100))
        rows = list(
            OutboundMessage.objects.select_for_update(skip_locked=True)
            .filter(
                organization_id=organization.id,
                status=BridgeOutboundStatus.PENDING.value,
                available_at__lte=timezone.now(),
            )
            .order_by("created_at")[:limit]
        )
        for outbound in rows:
            outbound.status = BridgeOutboundStatus.PROCESSING.value
            outbound.save(update_fields=["status", "updated_at"])
        return rows

    @staticmethod
    @transaction.atomic
    def record_delivery_status(
        *,
        organization,
        message_id,
        status: str,
        reason: str = "",
    ) -> OutboundMessage:
        outbound = (
            OutboundMessage.objects.select_for_update()
            .filter(
                organization_id=organization.id,
                id=message_id,
            )
            .first()
        )
        if outbound is None:
            raise ValidationError({"message_id": "Outbound message not found"})

        if status == "sent":
            outbound.status = BridgeOutboundStatus.SENT.value
            outbound.sent_at = outbound.sent_at or timezone.now()
            outbound.error_reason = ""
            outbound.save(update_fields=["status", "sent_at", "error_reason", "updated_at"])
            _update_crm_message(outbound, MessageStatus.SENT.value)
            return outbound

        if status != "failed":
            raise ValidationError({"status": "Expected 'sent' or 'failed'"})

        outbound.attempts += 1
        outbound.error_reason = (reason or "send_failed")[:2000]
        if outbound.attempts >= MAX_DELIVERY_ATTEMPTS:
            outbound.status = BridgeOutboundStatus.DEAD_LETTER.value
            _update_crm_message(outbound, MessageStatus.FAILED.value)
        else:
            outbound.status = BridgeOutboundStatus.PENDING.value
            backoff = min(2**outbound.attempts, BACKOFF_CAP_SECONDS)
            outbound.available_at = timezone.now() + timedelta(seconds=backoff)
        outbound.save(
            update_fields=[
                "attempts",
                "error_reason",
                "status",
                "available_at",
                "updated_at",
            ]
        )
        return outbound


def _phone_for_queue(*, resolved, fallback: str) -> str:
    if resolved is not None and resolved.phone is not None:
        return resolved.phone.phone_e164
    value = str(fallback or "").strip()
    return value if value.startswith("+") else f"+{value}"


def _update_crm_message(outbound: OutboundMessage, status: str) -> None:
    message_id = (outbound.metadata or {}).get("crm_message_id")
    if not message_id:
        return
    Message.objects.filter(
        organization_id=outbound.organization_id,
        id=message_id,
    ).update(status=status, updated_at=timezone.now())
