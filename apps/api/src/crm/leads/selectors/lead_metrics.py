from django.db.models import Avg, Count

from crm.leads.models import Lead


def lead_metrics_for_organization(organization) -> dict:
    base = Lead.objects.filter(organization_id=organization.id)
    totals = base.aggregate(total=Count("id"), avg_score=Avg("score"))
    by_temperature = {
        item["temperature"]: item["count"]
        for item in base.values("temperature").annotate(count=Count("id"))
    }
    return {
        "total": totals["total"] or 0,
        "avg_score": float(totals["avg_score"] or 0),
        "by_temperature": by_temperature,
    }
