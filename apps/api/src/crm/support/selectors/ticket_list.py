from django.db.models import Q, QuerySet

from crm.support.models import SupportTicket


def ticket_list_for_organization(
    organization,
    *,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    client_id=None,
    contact_id=None,
    assigned_user_id=None,
    search: str | None = None,
) -> QuerySet[SupportTicket]:
    queryset = SupportTicket.objects.filter(organization_id=organization.id).select_related(
        "contact", "client", "assigned_user"
    )
    if status:
        queryset = queryset.filter(status=status)
    if priority:
        queryset = queryset.filter(priority=priority)
    if category:
        queryset = queryset.filter(category=category)
    if client_id:
        queryset = queryset.filter(client_id=client_id)
    if contact_id:
        queryset = queryset.filter(contact_id=contact_id)
    if assigned_user_id:
        queryset = queryset.filter(assigned_user_id=assigned_user_id)
    if search:
        queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))
    return queryset.order_by("-created_at")
