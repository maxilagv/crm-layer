from django.utils import timezone

from crm.notifications.domain.enums import NotificationDeliveryStatus
from crm.notifications.models import NotificationDelivery

from .whatsapp_owner_notifier import WhatsAppOwnerNotifier


class DeliveryRetryService:
    @staticmethod
    def retry_failed(*, organization=None, limit: int = 100) -> int:
        queryset = NotificationDelivery.objects.filter(
            status=NotificationDeliveryStatus.FAILED.value
        ).select_related("notification__recipient_user")
        if organization is not None:
            queryset = queryset.filter(organization_id=organization.id)
        retried = 0
        for delivery in queryset.order_by("created_at")[:limit]:
            delivery.attempts += 1
            delivery.status = NotificationDeliveryStatus.QUEUED.value
            delivery.last_error = ""
            delivery.sent_at = timezone.now()
            delivery.save(
                update_fields=["attempts", "status", "last_error", "sent_at", "updated_at"]
            )
            if delivery.channel == "whatsapp":
                notification = delivery.notification
                WhatsAppOwnerNotifier.queue(
                    notification=notification,
                    owner_user=notification.recipient_user,
                    body=f"{notification.title}\n{notification.body}".strip(),
                )
            retried += 1
        return retried
