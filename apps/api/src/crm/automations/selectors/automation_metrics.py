from django.db.models import Count

from crm.automations.models import AutomationRun


def automation_run_counts_by_status(organization):
    return dict(
        AutomationRun.objects.filter(organization_id=organization.id)
        .values("status")
        .annotate(count=Count("id"))
        .values_list("status", "count")
    )
