from crm.tasks.models import Task


def task_calendar_for_organization(organization, *, start, end):
    return Task.objects.filter(
        organization_id=organization.id,
        due_at__gte=start,
        due_at__lt=end,
    ).order_by("due_at")
