from crm.automations.models import AutomationRun


def automation_runs_for_organization(
    organization,
    *,
    rule_id=None,
    status: str | None = None,
    trigger_type: str | None = None,
    ordering: str = "-created_at",
):
    queryset = AutomationRun.objects.filter(organization_id=organization.id).select_related("rule")
    if rule_id:
        queryset = queryset.filter(rule_id=rule_id)
    if status:
        queryset = queryset.filter(status=status)
    if trigger_type:
        queryset = queryset.filter(trigger_type=trigger_type)
    if ordering.lstrip("-") not in {"created_at", "updated_at", "started_at", "status"}:
        ordering = "-created_at"
    return queryset.order_by(ordering)


def automation_run_get_for_organization(organization, run_id):
    return (
        AutomationRun.objects.filter(organization_id=organization.id, id=run_id)
        .select_related("rule")
        .prefetch_related("steps")
        .first()
    )
