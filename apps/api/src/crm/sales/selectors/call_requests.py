from crm.sales.models import SalesCallRequest


def call_requests_for_organization(
    organization,
    *,
    status: str | None = None,
    lead_id=None,
    ordering: str = "-requested_at",
):
    queryset = SalesCallRequest.objects.filter(organization_id=organization.id).select_related(
        "lead", "contact", "conversation"
    )
    if status:
        queryset = queryset.filter(status=status)
    if lead_id:
        queryset = queryset.filter(lead_id=lead_id)
    allowed = {
        "requested_at",
        "-requested_at",
        "scheduled_at",
        "-scheduled_at",
        "created_at",
        "-created_at",
    }
    return queryset.order_by(ordering if ordering in allowed else "-requested_at")


def call_request_get_for_organization(organization, call_request_id):
    return (
        SalesCallRequest.objects.filter(organization_id=organization.id, id=call_request_id)
        .select_related("lead", "contact", "conversation")
        .first()
    )
