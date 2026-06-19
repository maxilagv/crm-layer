from crm.notifications.models import Notification


def notifications_for_organization(
    organization,
    *,
    recipient_user=None,
    status: str | None = None,
    notification_type: str | None = None,
    ordering: str = "-created_at",
):
    queryset = Notification.objects.filter(organization_id=organization.id).select_related(
        "recipient_user"
    )
    if recipient_user is not None:
        queryset = queryset.filter(recipient_user=recipient_user)
    if status:
        queryset = queryset.filter(status=status)
    if notification_type:
        queryset = queryset.filter(type=notification_type)
    if ordering.lstrip("-") not in {"created_at", "updated_at", "priority", "status"}:
        ordering = "-created_at"
    return queryset.order_by(ordering)


def notification_get_for_organization(organization, notification_id):
    return Notification.objects.filter(organization_id=organization.id, id=notification_id).first()
