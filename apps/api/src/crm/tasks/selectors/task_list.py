from crm.tasks.models import Task


def task_list_for_organization(
    organization,
    *,
    status: str | None = None,
    priority: str | None = None,
    assigned_to_id=None,
    due_before=None,
    due_after=None,
    search: str | None = None,
    ordering: str = "-updated_at",
):
    queryset = Task.objects.filter(organization_id=organization.id).select_related(
        "contact", "lead", "client", "ticket", "conversation", "assigned_to"
    )
    if status:
        queryset = queryset.filter(status=status)
    if priority:
        queryset = queryset.filter(priority=priority)
    if assigned_to_id:
        queryset = queryset.filter(assigned_to_id=assigned_to_id)
    if due_before:
        queryset = queryset.filter(due_at__lte=due_before)
    if due_after:
        queryset = queryset.filter(due_at__gte=due_after)
    if search:
        queryset = queryset.filter(title__icontains=search)
    if ordering.lstrip("-") not in {"created_at", "updated_at", "due_at", "priority", "status"}:
        ordering = "-updated_at"
    return queryset.order_by(ordering)
