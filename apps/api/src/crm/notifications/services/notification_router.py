from crm.core.services.outbox import create_outbox_event
from crm.notifications.domain import events
from crm.notifications.domain.enums import (
    NotificationChannelType,
    NotificationDeliveryStatus,
    NotificationPriority,
)
from crm.notifications.models import NotificationDelivery

from .notification_rate_limiter import NotificationRateLimiter
from .whatsapp_owner_notifier import WhatsAppOwnerNotifier


class NotificationRouter:
    @staticmethod
    def route(*, notification, organization) -> list[NotificationDelivery]:
        recipient = notification.recipient_user or getattr(organization, "owner", None)
        if recipient is None:
            return []
        deliveries: list[NotificationDelivery] = []

        dashboard = _queue_dashboard_delivery(notification=notification)
        deliveries.append(dashboard)

        if notification.priority in (
            NotificationPriority.HIGH.value,
            NotificationPriority.URGENT.value,
        ):
            decision = NotificationRateLimiter.can_deliver(
                notification=notification,
                recipient_user=recipient,
                channel=NotificationChannelType.WHATSAPP.value,
            )
            if decision.allowed:
                body = f"{notification.title}\n{notification.body}".strip()
                deliveries.append(
                    WhatsAppOwnerNotifier.queue(
                        notification=notification, owner_user=recipient, body=body
                    )
                )
            else:
                create_outbox_event(
                    event_type=events.NOTIFICATION_SUPPRESSED,
                    organization_id=notification.organization_id,
                    payload={
                        "notification_id": str(notification.id),
                        "channel": NotificationChannelType.WHATSAPP.value,
                        "reason": decision.reason,
                    },
                )
        return deliveries


def _queue_dashboard_delivery(*, notification) -> NotificationDelivery:
    key = f"dashboard:{notification.id}"
    delivery, _ = NotificationDelivery.objects.get_or_create(
        organization_id=notification.organization_id,
        notification=notification,
        channel=NotificationChannelType.DASHBOARD.value,
        idempotency_key=key,
        defaults={"status": NotificationDeliveryStatus.QUEUED.value},
    )
    return delivery
