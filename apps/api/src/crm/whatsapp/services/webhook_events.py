import hashlib
import json
from dataclasses import dataclass

from django.db import IntegrityError, transaction

from crm.core.services.outbox import create_outbox_event
from crm.whatsapp.domain import events
from crm.whatsapp.domain.enums import WebhookEventStatus
from crm.whatsapp.models import WhatsAppPhoneNumber, WhatsAppWebhookEvent
from crm.whatsapp.services.payload_parser import (
    classify_event_type,
    extract_phone_number_id,
    resolve_event_id,
)
from crm.whatsapp.services.webhook_verification import truncate_signature


@dataclass(frozen=True)
class WebhookPersistResult:
    event: WhatsAppWebhookEvent
    created: bool


def _malformed_event_id(raw_body: bytes) -> str:
    return "malformed:" + hashlib.sha256(raw_body).hexdigest()


def _organization_id_for_payload(payload: dict):
    phone_number_id = extract_phone_number_id(payload)
    if not phone_number_id:
        return None
    phone_number = WhatsAppPhoneNumber.objects.filter(phone_number_id=phone_number_id).first()
    return phone_number.organization_id if phone_number else None


@transaction.atomic
def persist_valid_webhook_event(
    *,
    raw_body: bytes,
    signature_header: str,
) -> WebhookPersistResult:
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        event = WhatsAppWebhookEvent.objects.create(
            organization_id=None,
            event_id=_malformed_event_id(raw_body),
            event_type="unknown",
            raw_payload={"malformed": True},
            signature=truncate_signature(signature_header),
            status=WebhookEventStatus.FAILED,
            error_message=f"Malformed JSON: {exc}"[:500],
        )
        return WebhookPersistResult(event=event, created=True)

    event_id = resolve_event_id(payload)
    organization_id = _organization_id_for_payload(payload)
    event_type = classify_event_type(payload)
    existing = WhatsAppWebhookEvent.objects.filter(
        organization_id=organization_id,
        event_id=event_id,
    ).first()
    if existing is not None:
        duplicate_count = int((existing.metadata or {}).get("duplicate_count", 0)) + 1
        existing.metadata = {**(existing.metadata or {}), "duplicate_count": duplicate_count}
        existing.save(update_fields=["metadata", "updated_at"])
        return WebhookPersistResult(event=existing, created=False)

    try:
        event = WhatsAppWebhookEvent.objects.create(
            organization_id=organization_id,
            event_id=event_id,
            event_type=event_type,
            raw_payload=payload,
            signature=truncate_signature(signature_header),
            status=WebhookEventStatus.RECEIVED,
        )
    except IntegrityError:
        event = WhatsAppWebhookEvent.objects.filter(
            organization_id=organization_id,
            event_id=event_id,
        ).first()
        if event is None:
            raise
        duplicate_count = int((event.metadata or {}).get("duplicate_count", 0)) + 1
        event.metadata = {**(event.metadata or {}), "duplicate_count": duplicate_count}
        event.save(update_fields=["metadata", "updated_at"])
        return WebhookPersistResult(event=event, created=False)

    create_outbox_event(
        event_type=events.WEBHOOK_RECEIVED,
        organization_id=organization_id,
        payload={"webhook_event_id": str(event.id), "event_type": event_type},
    )
    from crm.whatsapp.tasks import process_webhook_event

    transaction.on_commit(lambda: process_webhook_event.delay(str(event.id)))
    return WebhookPersistResult(event=event, created=True)
