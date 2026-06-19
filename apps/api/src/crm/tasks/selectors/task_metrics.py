from django.db.models import Count

from crm.tasks.models import Task


def task_counts_by_status(organization):
    return dict(
        Task.objects.filter(organization_id=organization.id)
        .values("status")
        .annotate(count=Count("id"))
        .values_list("status", "count")
    )
