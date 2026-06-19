from celery import shared_task

from crm.automations.models import AutomationAction, AutomationRule
from crm.automations.services.action_executor import ActionExecutor
from crm.automations.services.automation_engine import AutomationEngine
from crm.automations.services.trigger_dispatcher import TriggerDispatcher
from crm.organizations.models import Organization


@shared_task(name="automations.dispatch_trigger")
def dispatch_trigger(
    organization_id: str, trigger_type: str, payload: dict, trigger_event_id: str = ""
):
    organization = Organization.objects.get(id=organization_id)
    runs = TriggerDispatcher.dispatch(
        organization=organization,
        trigger_type=trigger_type,
        payload=payload,
        trigger_event_id=trigger_event_id,
    )
    return [str(run.id) for run in runs]


@shared_task(name="automations.execute_rule")
def execute_rule(rule_id: str, payload: dict, trigger_event_id: str = "") -> str:
    rule = AutomationRule.objects.get(id=rule_id)
    run = AutomationEngine.execute_rule(
        rule=rule,
        trigger_payload=payload,
        trigger_event_id=trigger_event_id,
    )
    return str(run.id)


@shared_task(name="automations.execute_action")
def execute_action(action_id: str, payload: dict) -> dict:
    action = AutomationAction.objects.select_related("rule").get(id=action_id)
    organization = Organization.objects.get(id=action.organization_id)
    result = ActionExecutor.execute(organization=organization, action=action, payload=payload)
    return {
        "success": result.success,
        "result": result.result,
        "error_code": result.error_code,
        "error_message": result.error_message,
    }
