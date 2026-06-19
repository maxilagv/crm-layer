from crm.leads.models import Lead


def lead_get_for_organization(organization, lead_id):
    return (
        Lead.objects.filter(organization_id=organization.id, id=lead_id)
        .select_related("contact")
        .prefetch_related("score_snapshots", "stage_history", "sources")
        .first()
    )
