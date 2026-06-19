from django.core.management.base import BaseCommand

from crm.automations.domain.enums import AutomationActionType, AutomationTriggerType
from crm.automations.models import AutomationRule
from crm.automations.services.automation_rule_service import AutomationRuleService
from crm.notifications.domain.enums import NotificationPriority, NotificationType
from crm.organizations.models import Organization

DEFAULT_RULES = [
    {
        "name": "Hot lead owner notification",
        "trigger_type": AutomationTriggerType.LEAD_BECAME_HOT.value,
        "conditions": [{"field": "score", "operator": "gte", "value": 80}],
        "actions": [
            {
                "type": AutomationActionType.NOTIFY_OWNER.value,
                "configuration": {
                    "system_allowed": True,
                    "notification_type": NotificationType.HOT_LEAD.value,
                    "title": "Lead caliente",
                    "body": "Lead con score {score}",
                    "priority": NotificationPriority.URGENT.value,
                    "resource_type": "lead",
                    "resource_id_field": "lead_id",
                },
            },
            {
                "type": AutomationActionType.CREATE_TASK.value,
                "configuration": {
                    "system_allowed": True,
                    "title": "Llamar lead caliente",
                    "priority": "urgent",
                },
            },
        ],
    },
    {
        "name": "Urgent ticket owner notification",
        "trigger_type": AutomationTriggerType.TICKET_CREATED.value,
        "conditions": [{"field": "priority", "operator": "in", "value": ["urgent", "critical"]}],
        "actions": [
            {
                "type": AutomationActionType.NOTIFY_OWNER.value,
                "configuration": {
                    "system_allowed": True,
                    "notification_type": NotificationType.URGENT_TICKET.value,
                    "title": "Ticket urgente",
                    "body": "{title}",
                    "priority": NotificationPriority.URGENT.value,
                    "resource_type": "support_ticket",
                    "resource_id_field": "ticket_id",
                },
            }
        ],
    },
    {
        "name": "Task due soon reminder",
        "trigger_type": AutomationTriggerType.TASK_DUE.value,
        "actions": [
            {
                "type": AutomationActionType.NOTIFY_OWNER.value,
                "configuration": {
                    "system_allowed": True,
                    "notification_type": NotificationType.TASK_DUE.value,
                    "title": "Tarea por vencer",
                    "body": "{title}",
                    "priority": NotificationPriority.HIGH.value,
                    "resource_type": "task",
                    "resource_id_field": "task_id",
                },
            }
        ],
    },
]


class Command(BaseCommand):
    help = "Seed default automation rules idempotently."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default=None)

    def handle(self, *args, **options):
        organizations = (
            Organization.objects.filter(id=options["organization_id"])
            if options["organization_id"]
            else Organization.objects.all()
        )
        created = 0
        for organization in organizations:
            for raw in DEFAULT_RULES:
                exists = organization.id and _rule_exists(organization, raw["name"])
                if exists:
                    continue
                AutomationRuleService.create(
                    organization=organization,
                    name=raw["name"],
                    trigger_type=raw["trigger_type"],
                    conditions=raw.get("conditions", []),
                    actions=raw.get("actions", []),
                    metadata={"seeded": True},
                )
                created += 1
        self.stdout.write(self.style.SUCCESS(f"{created} automation rules created"))


def _rule_exists(organization, name: str) -> bool:
    return AutomationRule.objects.filter(organization_id=organization.id, name=name).exists()
