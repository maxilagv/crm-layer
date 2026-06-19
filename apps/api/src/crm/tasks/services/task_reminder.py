from django.db import transaction
from django.utils import timezone

from crm.core.services.outbox import create_outbox_event
from crm.notifications.domain.enums import NotificationPriority, NotificationType
from crm.notifications.services.notification_service import NotificationService
from crm.organizations.models import Organization
from crm.tasks.domain import events
from crm.tasks.domain.enums import TaskPriority, TaskReminderStatus
from crm.tasks.domain.rules import can_send_reminder
from crm.tasks.models import TaskReminder


class TaskReminderService:
    @staticmethod
    @transaction.atomic
    def send_due(*, organization=None, now=None, limit: int = 100) -> int:
        now = now or timezone.now()
        queryset = (
            TaskReminder.objects.select_for_update()
            .select_related("task")
            .filter(
                status=TaskReminderStatus.PENDING.value,
                remind_at__lte=now,
            )
        )
        if organization is not None:
            queryset = queryset.filter(organization_id=organization.id)
        sent = 0
        for reminder in queryset.order_by("remind_at")[:limit]:
            task = reminder.task
            if not can_send_reminder(task):
                reminder.status = TaskReminderStatus.EXPIRED.value
                reminder.save(update_fields=["status", "updated_at"])
                continue
            org = organization or Organization.objects.select_related("owner").get(
                id=task.organization_id
            )
            notification, _ = NotificationService.notify_owner(
                organization=org,
                notification_type=NotificationType.TASK_DUE.value,
                title=f"Tarea pendiente: {task.title}",
                body=_body_for_task(task),
                priority=_notification_priority(task.priority),
                resource_type="task",
                resource_id=task.id,
                deduplication_key=f"task-reminder:{reminder.id}",
            )
            reminder.mark_sent(notification_id=notification.id)
            create_outbox_event(
                event_type=events.TASK_REMINDER_SENT,
                organization_id=task.organization_id,
                payload={"task_id": str(task.id), "reminder_id": str(reminder.id)},
            )
            sent += 1
        return sent


def _body_for_task(task) -> str:
    due = task.due_at.isoformat() if task.due_at else "sin fecha"
    return (
        f"Vence: {due}.\n"
        "Responder: HECHO, PENDIENTE, POSPONER 2H, POSPONER 1D, MANANA 10 o CANCELAR."
    )


def _notification_priority(task_priority: str) -> str:
    if task_priority == TaskPriority.URGENT.value:
        return NotificationPriority.URGENT.value
    if task_priority == TaskPriority.HIGH.value:
        return NotificationPriority.HIGH.value
    return NotificationPriority.MEDIUM.value
