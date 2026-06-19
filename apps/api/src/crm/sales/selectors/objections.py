from crm.sales.models import SalesObjection


def objections_for_lead(lead):
    return SalesObjection.objects.filter(
        organization_id=lead.organization_id,
        lead=lead,
    ).order_by("-created_at")
