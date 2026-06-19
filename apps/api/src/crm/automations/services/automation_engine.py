from django.db import IntegrityError, transaction

from crm.automations.domain.enums import (
    AutomationRunStatus,
    AutomationStepStatus,
    AutomationStepType,
)
from crm.automations.domain.rules import has_automation_loop
from crm.automations.models import AutomationRun
from crm.core.services.outbox import create_outbox_event
from crm.organizations.models import Organization

from .action_executor import ActionExecutor
from .automation_run_logger import AutomationRunLogger
from .condition_evaluator import ConditionEvaluator


class AutomationEngine:
    @staticmethod
    @transaction.atomic
    def execute_rule(*, rule, trigger_payload: dict, trigger_event_id: str = ""):
        organization = Organization.objects.select_related("owner").get(id=rule.organization_id)
        if not rule.is_enabled:
            return _skipped_run(rule, trigger_payload, trigger_event_id, "rule_disabled")
        if has_automation_loop(trigger_payload):
            return _skipped_run(
                rule, trigger_payload, trigger_event_id, "automation_loop_prevented"
            )
        try:
            run = AutomationRunLogger.start_run(
                rule=rule,
                trigger_type=rule.trigger_type,
                trigger_payload=trigger_payload,
                trigger_event_id=trigger_event_id,
            )
        except IntegrityError:
            return AutomationRun.objects.get(
                organization_id=rule.organization_id,
                rule=rule,
                trigger_event_id=trigger_event_id,
            )

        if not _conditions_pass(rule=rule, run=run, payload=trigger_payload):
            run.finish(AutomationRunStatus.SKIPPED.value, reason="conditions_failed")
            return run

        failures = 0
        executed = 0
        for action in _actions_for_rule(rule):
            result = ActionExecutor.execute(
                organization=organization, action=action, payload=trigger_payload
            )
            executed += 1
            action_ref = action if getattr(action, "pk", None) else None
            AutomationRunLogger.step(
                run=run,
                step_type=AutomationStepType.ACTION.value,
                name=action.action_type,
                action=action_ref,
                status=AutomationStepStatus.SUCCESS.value
                if result.success
                else AutomationStepStatus.FAILED.value,
                input_payload=action.configuration,
                output_payload=result.result,
                error_code=result.error_code,
                error_message=result.error_message,
            )
            if not result.success:
                failures += 1
        status = (
            AutomationRunStatus.SUCCESS.value
            if failures == 0
            else AutomationRunStatus.FAILED.value
            if failures == executed
            else AutomationRunStatus.PARTIALLY_FAILED.value
        )
        run.finish(status, reason=f"actions_executed:{executed}:failures:{failures}")
        create_outbox_event(
            event_type="automation.run_finished.v1",
            organization_id=rule.organization_id,
            payload={"run_id": str(run.id), "status": status},
        )
        return run


def _conditions_pass(*, rule, run, payload: dict) -> bool:
    condition_rows = list(rule.condition_rows.order_by("order", "created_at"))
    if condition_rows:
        for condition in condition_rows:
            result = ConditionEvaluator.evaluate_condition(condition=condition, payload=payload)
            AutomationRunLogger.step(
                run=run,
                step_type=AutomationStepType.CONDITION.value,
                name=condition.field_path,
                condition=condition,
                status=AutomationStepStatus.SUCCESS.value
                if result.passed
                else AutomationStepStatus.SKIPPED.value,
                input_payload={"field_path": condition.field_path, "operator": condition.operator},
                output_payload={"passed": result.passed, "reason": result.reason},
            )
            if not result.passed:
                return False
        return True
    for raw in rule.conditions or []:
        result = ConditionEvaluator.evaluate_inline(raw_condition=raw, payload=payload)
        AutomationRunLogger.step(
            run=run,
            step_type=AutomationStepType.CONDITION.value,
            name=str(raw.get("field") or raw.get("field_path") or "inline"),
            status=AutomationStepStatus.SUCCESS.value
            if result.passed
            else AutomationStepStatus.SKIPPED.value,
            input_payload=raw,
            output_payload={"passed": result.passed, "reason": result.reason},
        )
        if not result.passed:
            return False
    return True


def _actions_for_rule(rule):
    rows = list(rule.action_rows.order_by("order", "created_at"))
    if rows:
        return rows
    from crm.automations.models import AutomationAction

    actions = []
    for index, raw in enumerate(rule.actions or []):
        actions.append(
            AutomationAction(
                id=None,
                organization_id=rule.organization_id,
                rule=rule,
                order=index,
                action_type=raw.get("type") or raw.get("action_type"),
                configuration=raw.get("configuration", raw),
                required_permission=raw.get("required_permission", ""),
            )
        )
    return actions


def _skipped_run(rule, payload, trigger_event_id: str, reason: str):
    if trigger_event_id:
        run, _ = AutomationRun.objects.get_or_create(
            organization_id=rule.organization_id,
            rule=rule,
            trigger_event_id=trigger_event_id,
            defaults={
                "trigger_type": rule.trigger_type,
                "trigger_payload": payload,
                "status": AutomationRunStatus.SKIPPED.value,
                "reason": reason,
            },
        )
        return run
    return AutomationRun.objects.create(
        organization_id=rule.organization_id,
        rule=rule,
        trigger_type=rule.trigger_type,
        trigger_event_id="",
        trigger_payload=payload,
        status=AutomationRunStatus.SKIPPED.value,
        reason=reason,
    )
