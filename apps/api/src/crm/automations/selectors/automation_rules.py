from crm.automations.models import AutomationRule


def automation_rules_for_organization(
    organization,
    *,
    trigger_type: str | None = None,
    is_enabled=None,
    ordering: str = "priority",
):
    queryset = AutomationRule.objects.filter(organization_id=organization.id).select_related(
        "created_by"
    )
    if trigger_type:
        queryset = queryset.filter(trigger_type=trigger_type)
    if is_enabled is not None:
        queryset = queryset.filter(is_enabled=is_enabled)
    if ordering.lstrip("-") not in {"created_at", "updated_at", "priority", "name"}:
        ordering = "priority"
    return queryset.order_by(ordering, "created_at")


def automation_rule_get_for_organization(organization, rule_id):
    return (
        AutomationRule.objects.filter(organization_id=organization.id, id=rule_id)
        .prefetch_related("triggers", "condition_rows", "action_rows")
        .first()
    )
