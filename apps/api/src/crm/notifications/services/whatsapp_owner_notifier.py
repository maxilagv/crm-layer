from django.db import transaction
from django.utils import timezone

from crm.core.services.outbox import create_outbox_event
from crm.notifications.domain import events
from crm.notifications.domain.enums import (
    NotificationChannelType,
    NotificationDeliveryStatus,
)
from crm.notifications.models import NotificationDelivery

OWNER_WHATSAPP_OUTBOX_EVENT = "notification.owner_whatsapp_message.queued.v1"


class WhatsAppOwnerNotifier:
    """Queue owner WhatsApp notifications without calling Meta directly."""

    @staticmethod
    @transaction.atomic
    def queue(*, notification, owner_user, body: str) -> NotificationDelivery:
        key = f"owner-whatsapp:{notification.id}"
        delivery, created = NotificationDelivery.objects.get_or_create(
            organization_id=notification.organization_id,
            notification=notification,
            channel=NotificationChannelType.WHATSAPP.value,
            idempotency_key=key,
            defaults={
                "status": NotificationDeliveryStatus.QUEUED.value,
                "attempts": 1,
                "sent_at": timezone.now(),
                "metadata": {"owner_user_id": str(getattr(owner_user, "id", "") or "")},
            },
        )
        if not created and delivery.status == NotificationDeliveryStatus.SENT.value:
            return delivery
        if not created and delivery.status != NotificationDeliveryStatus.QUEUED.value:
            delivery.status = NotificationDeliveryStatus.QUEUED.value
            delivery.attempts += 1
            delivery.sent_at = timezone.now()
            delivery.save(update_fields=["status", "attempts", "sent_at", "updated_at"])
        create_outbox_event(
            event_type=OWNER_WHATSAPP_OUTBOX_EVENT,
            organization_id=notification.organization_id,
            payload={
                "event_type": OWNER_WHATSAPP_OUTBOX_EVENT,
                "organization_id": str(notification.organization_id),
                "data": {
                    "notification_id": str(notification.id),
                    "delivery_id": str(delivery.id),
                    "owner_user_id": str(getattr(owner_user, "id", "") or ""),
                    "owner_phone": getattr(owner_user, "phone", ""),
                    "body": body[:2000],
                },
            },
        )
        create_outbox_event(
            event_type=events.NOTIFICATION_DELIVERY_QUEUED,
            organization_id=notification.organization_id,
            payload={"notification_id": str(notification.id), "delivery_id": str(delivery.id)},
        )
        return delivery
