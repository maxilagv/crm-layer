from celery import shared_task

from crm.conversations.models import Message
from crm.organizations.models import Organization
from crm.tasks.services.task_command_parser import TaskCommandParser
from crm.tasks.services.task_escalation import TaskEscalationService
from crm.tasks.services.task_extractor import TaskExtractor
from crm.tasks.services.task_reminder import TaskReminderService


@shared_task(name="tasks.extract_tasks_from_message")
def extract_tasks_from_message(message_id: str, auto_confirm: bool = False) -> dict:
    message = Message.objects.select_related("conversation").get(id=message_id)
    organization = Organization.objects.get(id=message.organization_id)
    result = TaskExtractor.extract_from_message(
        organization=organization,
        conversation=message.conversation,
        message=message,
        auto_confirm=auto_confirm,
    )
    return {
        "created_count": result.created_count,
        "skipped_count": result.skipped_count,
        "ai_run_id": str(result.ai_run_id or ""),
    }


@shared_task(name="tasks.send_due_reminders")
def send_due_reminders(organization_id: str | None = None) -> int:
    organization = Organization.objects.get(id=organization_id) if organization_id else None
    return TaskReminderService.send_due(organization=organization)


@shared_task(name="tasks.escalate_overdue_tasks")
def escalate_overdue_tasks(organization_id: str | None = None) -> int:
    organization = Organization.objects.get(id=organization_id) if organization_id else None
    return TaskEscalationService.escalate_overdue(organization=organization)


@shared_task(name="tasks.parse_owner_command")
def parse_owner_command(message_id: str, task_id: str | None = None) -> str:
    from crm.tasks.models import Task

    message = Message.objects.select_related("contact").get(id=message_id)
    organization = Organization.objects.select_related("owner").get(id=message.organization_id)
    task = (
        Task.objects.filter(id=task_id, organization_id=organization.id).first()
        if task_id
        else None
    )
    command = TaskCommandParser.parse_and_apply(
        organization=organization,
        message=message,
        task=task,
        actor=organization.owner,
    )
    return str(command.id)
