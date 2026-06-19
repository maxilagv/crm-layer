from crm.notifications.models import NotificationDigest


def digests_for_user(organization, recipient_user):
    return NotificationDigest.objects.filter(
        organization_id=organization.id,
        recipient_user=recipient_user,
    ).order_by("-period_end")
