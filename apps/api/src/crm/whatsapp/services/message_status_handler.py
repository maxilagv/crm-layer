from django.db import IntegrityError, transaction
from django.utils import timezone

from crm.core.logging import sanitize
from crm.core.services.outbox import create_outbox_event
from crm.whatsapp.domain import events
from crm.whatsapp.domain.enums import OutboundMessageStatus, WhatsAppDeliveryStatus
from crm.whatsapp.models import (
    WhatsAppMessageStatus,
    WhatsAppOutboundMessage,
    WhatsAppWebhookEvent,
)
from crm.whatsapp.services.payload_parser import iter_changes, parse_meta_timestamp


def _normalize_status(value: str) -> str:
    allowed = {choice.value for choice in WhatsAppDeliveryStatus}
    return value if value in allowed else WhatsAppDeliveryStatus.UNKNOWN.value


def _extract_error(status_payload: dict) -> tuple[str, str]:
    errors = status_payload.get("errors") or []
    if not errors:
        return "", ""
    error = errors[0]
    return str(error.get("code") or ""), str(error.get("message") or error.get("title") or "")[:500]


def _update_outbound_from_status(outbound: WhatsAppOutboundMessage, status_row) -> None:
    status = status_row.status
    fields = ["updated_at"]
    if status == WhatsAppDeliveryStatus.SENT:
        outbound.status = OutboundMessageStatus.SENT
        outbound.sent_at = outbound.sent_at or status_row.status_timestamp or timezone.now()
        fields += ["status", "sent_at"]
    elif status == WhatsAppDeliveryStatus.DELIVERED:
        outbound.status = OutboundMessageStatus.DELIVERED
        outbound.delivered_at = (
            outbound.delivered_at or status_row.status_timestamp or timezone.now()
        )
        fields += ["status", "delivered_at"]
    elif status == WhatsAppDeliveryStatus.READ:
        outbound.status = OutboundMessageStatus.READ
        outbound.delivered_at = (
            outbound.delivered_at or status_row.status_timestamp or timezone.now()
        )
        outbound.read_at = outbound.read_at or status_row.status_timestamp or timezone.now()
        fields += ["status", "delivered_at", "read_at"]
    elif status == WhatsAppDeliveryStatus.FAILED:
        outbound.status = OutboundMessageStatus.FAILED
        outbound.failed_at = outbound.failed_at or status_row.status_timestamp or timezone.now()
        outbound.error_code = status_row.error_code
        outbound.error_message = status_row.error_message
        fields += ["status", "failed_at", "error_code", "error_message"]
    else:
        return
    outbound.save(update_fields=fields)


@transaction.atomic
def handle_message_statuses(webhook_event: WhatsAppWebhookEvent) -> int:
    processed = 0
    for change in iter_changes(webhook_event.raw_payload):
        for status_payload in change.value.get("statuses") or []:
            external_message_id = str(status_payload.get("id") or "")
            if not external_message_id:
                continue
            status = _normalize_status(str(status_payload.get("status") or ""))
            status_timestamp = parse_meta_timestamp(status_payload.get("timestamp"))
            error_code, error_message = _extract_error(status_payload)
            outbound = (
                WhatsAppOutboundMessage.objects.filter(
                    organization_id=webhook_event.organization_id,
                    external_message_id=external_message_id,
                )
                .select_for_update()
                .first()
            )
            try:
                status_row, created = WhatsAppMessageStatus.objects.get_or_create(
                    organization_id=webhook_event.organization_id,
                    external_message_id=external_message_id,
                    status=status,
                    status_timestamp=status_timestamp,
                    defaults={
                        "outbound_message": outbound,
                        "error_code": error_code,
                        "error_message": error_message,
                        "raw_status": sanitize(status_payload),
                        "webhook_event": webhook_event,
                    },
                )
            except IntegrityError:
                created = False
                status_row = WhatsAppMessageStatus.objects.filter(
                    organization_id=webhook_event.organization_id,
                    external_message_id=external_message_id,
                    status=status,
                    status_timestamp=status_timestamp,
                ).first()
            if not created:
                processed += 1
                continue
            if outbound is not None:
                _update_outbound_from_status(outbound, status_row)
            create_outbox_event(
                event_type=events.MESSAGE_STATUS_UPDATED,
                organization_id=webhook_event.organization_id,
                payload={
                    "external_message_id": external_message_id,
                    "status": status,
                    "outbound_message_id": str(outbound.id) if outbound else None,
                },
            )
            processed += 1
    return processed
