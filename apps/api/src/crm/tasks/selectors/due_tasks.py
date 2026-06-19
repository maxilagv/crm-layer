from django.utils import timezone

from crm.tasks.models import Task


def due_tasks_for_organization(organization, *, now=None):
    now = now or timezone.now()
    return Task.objects.filter(
        organization_id=organization.id,
        due_at__lte=now,
        status__in=["pending", "in_progress", "waiting", "snoozed"],
    ).order_by("due_at")
