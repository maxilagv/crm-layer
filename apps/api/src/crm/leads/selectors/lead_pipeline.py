from django.db.models import Count

from crm.leads.models import Lead


def lead_pipeline_for_organization(organization) -> list[dict]:
    return list(
        Lead.objects.filter(organization_id=organization.id)
        .values("stage")
        .annotate(count=Count("id"))
        .order_by("stage")
    )
