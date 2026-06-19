from celery import shared_task

from crm.notifications.services.delivery_retry import DeliveryRetryService
from crm.notifications.services.digest_builder import DigestBuilder
from crm.organizations.models import Organization


@shared_task(name="notifications.retry_failed_delivery")
def retry_failed_delivery(organization_id: str | None = None) -> int:
    organization = Organization.objects.get(id=organization_id) if organization_id else None
    return DeliveryRetryService.retry_failed(organization=organization)


@shared_task(name="notifications.build_daily_digest")
def build_daily_digest(organization_id: str | None = None) -> int:
    organizations = (
        Organization.objects.filter(id=organization_id).select_related("owner")
        if organization_id
        else Organization.objects.select_related("owner").all()
    )
    count = 0
    for organization in organizations:
        DigestBuilder.build_daily(organization=organization, recipient_user=organization.owner)
        count += 1
    return count


@shared_task(name="notifications.send_notification")
def send_notification(notification_id: str) -> str:
    from crm.notifications.models import Notification
    from crm.notifications.services.notification_router import NotificationRouter
    from crm.organizations.models import Organization

    notification = Notification.objects.get(id=notification_id)
    organization = Organization.objects.select_related("owner").get(id=notification.organization_id)
    NotificationRouter.route(notification=notification, organization=organization)
    return str(notification.id)
