from django.db import IntegrityError, transaction

from crm.core.services.outbox import create_outbox_event
from crm.tasks.domain import events
from crm.tasks.domain.enums import TaskReminderStatus
from crm.tasks.models import TaskReminder


class TaskScheduler:
    @staticmethod
    @transaction.atomic
    def schedule_reminder(*, task, remind_at, channel: str = "whatsapp", actor=None, metadata=None):
        if task.status in ("completed", "cancelled"):
            raise ValueError("Cannot schedule reminder for completed/cancelled task")
        try:
            reminder, created = TaskReminder.objects.get_or_create(
                organization_id=task.organization_id,
                task=task,
                channel=channel,
                remind_at=remind_at,
                status=TaskReminderStatus.PENDING.value,
                defaults={"created_by_id": getattr(actor, "id", None), "metadata": metadata or {}},
            )
        except IntegrityError:
            reminder = TaskReminder.objects.get(
                organization_id=task.organization_id,
                task=task,
                channel=channel,
                remind_at=remind_at,
                status=TaskReminderStatus.PENDING.value,
            )
            created = False
        if created:
            create_outbox_event(
                event_type=events.TASK_REMINDER_SCHEDULED,
                organization_id=task.organization_id,
                payload={"task_id": str(task.id), "reminder_id": str(reminder.id)},
            )
        return reminder, created
