"""Tenant-scoped client listing."""

from django.db.models import Q, QuerySet

from crm.clients.models import Client


def client_list_for_organization(
    organization,
    *,
    status: str | None = None,
    support_level: str | None = None,
    service_plan: str | None = None,
    search: str | None = None,
) -> QuerySet[Client]:
    queryset = Client.objects.filter(organization_id=organization.id).select_related("contact")
    if status:
        queryset = queryset.filter(status=status)
    if support_level:
        queryset = queryset.filter(support_level=support_level)
    if service_plan:
        queryset = queryset.filter(service_plan=service_plan)
    if search:
        queryset = queryset.filter(
            Q(display_name__icontains=search) | Q(contact__display_name__icontains=search)
        )
    return queryset.order_by("-created_at")
