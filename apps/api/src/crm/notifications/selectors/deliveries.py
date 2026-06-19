from crm.notifications.models import NotificationDelivery


def deliveries_for_notification(notification):
    return NotificationDelivery.objects.filter(notification=notification).order_by("-created_at")
