from crm.automations.domain.events import AUTOMATION_TRIGGER_DISPATCHED
from crm.automations.models import AutomationRule
from crm.core.services.outbox import create_outbox_event

from .automation_engine import AutomationEngine


class TriggerDispatcher:
    @staticmethod
    def dispatch(*, organization, trigger_type: str, payload: dict, trigger_event_id: str = ""):
        runs = []
        rules = AutomationRule.objects.filter(
            organization_id=organization.id,
            trigger_type=trigger_type,
        ).order_by("priority", "created_at")
        for rule in rules:
            runs.append(
                AutomationEngine.execute_rule(
                    rule=rule,
                    trigger_payload=payload,
                    trigger_event_id=trigger_event_id,
                )
            )
        create_outbox_event(
            event_type=AUTOMATION_TRIGGER_DISPATCHED,
            organization_id=organization.id,
            payload={
                "trigger_type": trigger_type,
                "trigger_event_id": trigger_event_id,
                "run_count": len(runs),
            },
        )
        return runs
