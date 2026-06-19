from django.utils import timezone

from crm.automations.domain.enums import AutomationRunStatus, AutomationStepStatus
from crm.automations.models import AutomationRun, AutomationRunStep


class AutomationRunLogger:
    @staticmethod
    def start_run(*, rule, trigger_type: str, trigger_payload: dict, trigger_event_id: str = ""):
        return AutomationRun.objects.create(
            organization_id=rule.organization_id,
            rule=rule,
            trigger_type=trigger_type,
            trigger_event_id=trigger_event_id,
            status=AutomationRunStatus.RUNNING.value,
            trigger_payload=trigger_payload,
        )

    @staticmethod
    def step(
        *,
        run,
        step_type: str,
        name: str,
        status: str = AutomationStepStatus.PENDING.value,
        action=None,
        condition=None,
        input_payload=None,
        output_payload=None,
        error_code: str = "",
        error_message: str = "",
    ):
        return AutomationRunStep.objects.create(
            organization_id=run.organization_id,
            automation_run=run,
            action=action,
            condition=condition,
            step_type=step_type,
            name=name[:255],
            status=status,
            input_payload=input_payload or {},
            output_payload=output_payload or {},
            error_code=error_code[:64],
            error_message=error_message[:2000],
            finished_at=timezone.now()
            if status
            in (
                AutomationStepStatus.SUCCESS.value,
                AutomationStepStatus.FAILED.value,
                AutomationStepStatus.BLOCKED.value,
                AutomationStepStatus.SKIPPED.value,
            )
            else None,
        )
