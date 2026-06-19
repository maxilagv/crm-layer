from django.db import IntegrityError, transaction
from django.utils import timezone

from crm.core.services.outbox import create_outbox_event
from crm.notifications.domain import events
from crm.notifications.domain.enums import DigestStatus, NotificationStatus, NotificationType
from crm.notifications.models import Notification, NotificationDigest


class DigestBuilder:
    @staticmethod
    @transaction.atomic
    def build_daily(*, organization, recipient_user, period_start=None, period_end=None):
        period_end = period_end or timezone.now()
        period_start = period_start or (period_end - timezone.timedelta(days=1))
        notifications = Notification.objects.filter(
            organization_id=organization.id,
            recipient_user=recipient_user,
            status=NotificationStatus.UNREAD.value,
            created_at__gte=period_start,
            created_at__lt=period_end,
        ).order_by("priority", "created_at")
        count = notifications.count()
        title = f"Resumen diario: {count} pendientes"
        body = "\n".join(f"- {n.title}" for n in notifications[:20])
        try:
            digest, created = NotificationDigest.objects.get_or_create(
                organization_id=organization.id,
                recipient_user=recipient_user,
                period_start=period_start,
                period_end=period_end,
                defaults={
                    "status": DigestStatus.BUILT.value,
                    "title": title,
                    "body": body,
                    "notification_count": count,
                },
            )
        except IntegrityError:
            digest = NotificationDigest.objects.get(
                organization_id=organization.id,
                recipient_user=recipient_user,
                period_start=period_start,
                period_end=period_end,
            )
            created = False
        if created:
            Notification.objects.create(
                organization_id=organization.id,
                recipient_user=recipient_user,
                type=NotificationType.DAILY_DIGEST.value,
                title=title,
                body=body,
                priority="low",
                resource_type="notification_digest",
                resource_id=digest.id,
                deduplication_key=f"digest:{recipient_user.id}:{period_start.isoformat()}:{period_end.isoformat()}",
            )
            create_outbox_event(
                event_type=events.NOTIFICATION_DIGEST_BUILT,
                organization_id=organization.id,
                payload={"digest_id": str(digest.id), "count": count},
            )
        return digest, created
