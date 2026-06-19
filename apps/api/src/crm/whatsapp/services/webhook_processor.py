import logging

from django.db import transaction
from django.utils import timezone

from crm.core.services.outbox import create_outbox_event
from crm.whatsapp.domain import events
from crm.whatsapp.domain.enums import WebhookEventStatus, WebhookEventType
from crm.whatsapp.models import WhatsAppWebhookEvent
from crm.whatsapp.services.inbound_message_handler import handle_inbound_messages
from crm.whatsapp.services.message_status_handler import handle_message_statuses

logger = logging.getLogger(__name__)


def process_event(webhook_event_id) -> WhatsAppWebhookEvent:
    with transaction.atomic():
        event = WhatsAppWebhookEvent.objects.select_for_update().get(id=webhook_event_id)
        if event.status in {
            WebhookEventStatus.PROCESSED,
            WebhookEventStatus.IGNORED,
            WebhookEventStatus.DUPLICATE,
        }:
            return event
        event.status = WebhookEventStatus.PROCESSING
        event.save(update_fields=["status", "updated_at"])

    try:
        processed_count = 0
        if event.event_type == WebhookEventType.MESSAGES:
            processed_count = handle_inbound_messages(event)
        elif event.event_type == WebhookEventType.STATUSES:
            processed_count = handle_message_statuses(event)
        else:
            event.mark_ignored("Unsupported WhatsApp webhook event type")
            return event

        if processed_count == 0:
            event.mark_ignored("No processable WhatsApp changes")
        else:
            with transaction.atomic():
                event = WhatsAppWebhookEvent.objects.select_for_update().get(id=webhook_event_id)
                event.status = WebhookEventStatus.PROCESSED
                event.processed_at = timezone.now()
                event.error_message = ""
                event.save(update_fields=["status", "processed_at", "error_message", "updated_at"])
                create_outbox_event(
                    event_type=events.WEBHOOK_PROCESSED,
                    organization_id=event.organization_id,
                    payload={"webhook_event_id": str(event.id), "processed_count": processed_count},
                )
    except Exception as exc:
        event = WhatsAppWebhookEvent.objects.get(id=webhook_event_id)
        event.mark_failed(exc)
        logger.exception(
            "WhatsApp webhook processing failed",
            extra={
                "event": "whatsapp.webhook.failed",
                "organization_id": str(event.organization_id) if event.organization_id else None,
                "metadata": {"webhook_event_id": str(event.id), "event_type": event.event_type},
            },
        )
        raise
    return event
