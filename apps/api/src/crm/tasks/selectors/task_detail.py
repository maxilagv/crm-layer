from crm.tasks.models import Task


def task_get_for_organization(organization, task_id):
    return (
        Task.objects.filter(organization_id=organization.id, id=task_id)
        .select_related("contact", "lead", "client", "ticket", "conversation", "assigned_to")
        .prefetch_related("reminders", "comments", "status_history", "sources")
        .first()
    )
