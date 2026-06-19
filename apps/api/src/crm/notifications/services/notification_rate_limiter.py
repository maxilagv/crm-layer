from datetime import timedelta

from django.utils import timezone

from crm.notifications.domain.rules import is_quiet_hours
from crm.notifications.domain.value_objects import DeliveryDecision
from crm.notifications.models import NotificationDelivery, NotificationPreference


class NotificationRateLimiter:
    @staticmethod
    def can_deliver(*, notification, recipient_user, channel: str, now=None) -> DeliveryDecision:
        now = now or timezone.now()
        preference = (
            NotificationPreference.objects.filter(
                organization_id=notification.organization_id,
                recipient_user=recipient_user,
                channel=channel,
                notification_type=notification.type,
            ).first()
            or NotificationPreference.objects.filter(
                organization_id=notification.organization_id,
                recipient_user=recipient_user,
                channel=channel,
                notification_type="",
            ).first()
        )
        if preference is not None:
            if not preference.is_enabled:
                return DeliveryDecision(False, "preference_disabled")
            if preference.digest_only:
                return DeliveryDecision(False, "digest_only")
            if is_quiet_hours(
                now.timetz().replace(tzinfo=None),
                preference.quiet_hours_start,
                preference.quiet_hours_end,
            ):
                return DeliveryDecision(False, "quiet_hours")
            max_per_hour = preference.max_per_hour
        else:
            max_per_hour = 5

        since = now - timedelta(hours=1)
        sent_count = NotificationDelivery.objects.filter(
            organization_id=notification.organization_id,
            channel=channel,
            status__in=["queued", "sent"],
            created_at__gte=since,
            notification__recipient_user=recipient_user,
        ).count()
        if sent_count >= max_per_hour:
            return DeliveryDecision(False, "rate_limited")
        return DeliveryDecision(True)
