from django.db.models import Avg, Count

from crm.sales.models import SalesCallRequest, SalesOpportunity


def sales_metrics_for_organization(organization) -> dict:
    opportunities = SalesOpportunity.objects.filter(organization_id=organization.id)
    calls = SalesCallRequest.objects.filter(organization_id=organization.id)
    return {
        "opportunities": opportunities.count(),
        "avg_probability": float(opportunities.aggregate(value=Avg("probability"))["value"] or 0),
        "open_call_requests": calls.exclude(
            status__in=["completed", "cancelled", "expired"]
        ).count(),
        "calls_by_status": {
            item["status"]: item["count"]
            for item in calls.values("status").annotate(count=Count("id"))
        },
    }
