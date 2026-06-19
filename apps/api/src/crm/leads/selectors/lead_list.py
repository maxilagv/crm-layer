from crm.leads.models import Lead


def lead_list_for_organization(
    organization,
    *,
    stage: str | None = None,
    status: str | None = None,
    temperature: str | None = None,
    search: str | None = None,
    ordering: str = "-updated_at",
):
    queryset = Lead.objects.filter(organization_id=organization.id).select_related("contact")
    if stage:
        queryset = queryset.filter(stage=stage)
    if status:
        queryset = queryset.filter(status=status)
    if temperature:
        queryset = queryset.filter(temperature=temperature)
    if search:
        queryset = queryset.filter(contact__display_name__icontains=search)
    allowed_ordering = {
        "created_at",
        "-created_at",
        "updated_at",
        "-updated_at",
        "score",
        "-score",
        "last_scored_at",
        "-last_scored_at",
    }
    return queryset.order_by(ordering if ordering in allowed_ordering else "-updated_at")
