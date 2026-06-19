from crm.notifications.models import NotificationPreference


def preferences_for_user(organization, recipient_user):
    return NotificationPreference.objects.filter(
        organization_id=organization.id,
        recipient_user=recipient_user,
    ).order_by("notification_type", "channel")
