from crm.sales.models import SalesOpportunity


def opportunities_for_organization(
    organization,
    *,
    stage: str | None = None,
    lead_id=None,
    ordering: str = "-updated_at",
):
    queryset = SalesOpportunity.objects.filter(organization_id=organization.id).select_related(
        "lead", "contact"
    )
    if stage:
        queryset = queryset.filter(stage=stage)
    if lead_id:
        queryset = queryset.filter(lead_id=lead_id)
    allowed = {
        "created_at",
        "-created_at",
        "updated_at",
        "-updated_at",
        "probability",
        "-probability",
    }
    return queryset.order_by(ordering if ordering in allowed else "-updated_at")


def opportunity_get_for_organization(organization, opportunity_id):
    return (
        SalesOpportunity.objects.filter(organization_id=organization.id, id=opportunity_id)
        .select_related("lead", "contact")
        .first()
    )
