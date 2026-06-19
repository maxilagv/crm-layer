from django.db import transaction

from crm.automations.models import (
    AutomationAction,
    AutomationCondition,
    AutomationRule,
    AutomationTrigger,
)


class AutomationRuleService:
    @staticmethod
    @transaction.atomic
    def create(
        *,
        organization,
        name: str,
        trigger_type: str,
        description: str = "",
        conditions: list | None = None,
        actions: list | None = None,
        is_enabled: bool = True,
        priority: int = 100,
        actor=None,
        metadata: dict | None = None,
    ) -> AutomationRule:
        rule = AutomationRule.objects.create(
            organization_id=organization.id,
            name=name[:255],
            description=description,
            trigger_type=trigger_type,
            conditions=conditions or [],
            actions=actions or [],
            is_enabled=is_enabled,
            priority=priority,
            created_by=actor,
            metadata=metadata or {},
        )
        AutomationTrigger.objects.create(
            organization_id=organization.id,
            rule=rule,
            trigger_type=trigger_type,
        )
        _replace_rows(rule=rule, conditions=conditions or [], actions=actions or [])
        return rule

    @staticmethod
    @transaction.atomic
    def update(*, rule, data: dict) -> AutomationRule:
        conditions = data.pop("conditions", None)
        actions = data.pop("actions", None)
        changed = []
        for field in ["name", "description", "trigger_type", "is_enabled", "priority", "metadata"]:
            if field in data:
                setattr(rule, field, data[field])
                changed.append(field)
        if conditions is not None:
            rule.conditions = conditions
            changed.append("conditions")
        if actions is not None:
            rule.actions = actions
            changed.append("actions")
        if changed:
            rule.save(update_fields=[*changed, "updated_at"])
        if "trigger_type" in changed:
            rule.triggers.update(trigger_type=rule.trigger_type)
        if conditions is not None or actions is not None:
            _replace_rows(
                rule=rule,
                conditions=rule.conditions
                if conditions is not None
                else list(rule.condition_rows.values()),
                actions=rule.actions if actions is not None else list(rule.action_rows.values()),
            )
        return rule

    @staticmethod
    def set_enabled(*, rule, enabled: bool) -> AutomationRule:
        if rule.is_enabled == enabled:
            return rule
        rule.is_enabled = enabled
        rule.save(update_fields=["is_enabled", "updated_at"])
        return rule


def _replace_rows(*, rule, conditions: list, actions: list) -> None:
    rule.condition_rows.all().delete()
    rule.action_rows.all().delete()
    for index, raw in enumerate(conditions):
        AutomationCondition.objects.create(
            organization_id=rule.organization_id,
            rule=rule,
            order=index,
            condition_type=raw.get("type", "field"),
            field_path=raw.get("field") or raw.get("field_path") or "",
            operator=raw.get("operator", "eq"),
            expected_value=raw.get("value", raw.get("expected_value")),
            configuration=raw,
        )
    for index, raw in enumerate(actions):
        AutomationAction.objects.create(
            organization_id=rule.organization_id,
            rule=rule,
            order=index,
            action_type=raw.get("type") or raw.get("action_type"),
            configuration=raw.get("configuration", raw),
            required_permission=raw.get("required_permission", ""),
            timeout_seconds=raw.get("timeout_seconds", 30),
        )
