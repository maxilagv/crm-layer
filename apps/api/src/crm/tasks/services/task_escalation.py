from django.db import transaction
from django.utils import timezone

from crm.notifications.domain.enums import NotificationPriority, NotificationType
from crm.notifications.services.notification_service import NotificationService
from crm.organizations.models import Organization
from crm.tasks.domain.enums import TaskStatus
from crm.tasks.domain.rules import should_mark_overdue
from crm.tasks.models import Task

from .task_completion import _change_status


class TaskEscalationService:
    @staticmethod
    @transaction.atomic
    def escalate_overdue(*, organization=None, now=None, limit: int = 100) -> int:
        now = now or timezone.now()
        queryset = Task.objects.select_for_update().filter(
            due_at__lt=now,
            status__in=["pending", "in_progress", "waiting", "snoozed"],
        )
        if organization is not None:
            queryset = queryset.filter(organization_id=organization.id)
        count = 0
        for task in queryset.order_by("due_at")[:limit]:
            if not should_mark_overdue(task, now=now):
                continue
            task = _change_status(task=task, status=TaskStatus.OVERDUE.value, reason="overdue")
            org = organization or Organization.objects.select_related("owner").get(
                id=task.organization_id
            )
            NotificationService.notify_owner(
                organization=org,
                notification_type=NotificationType.TASK_OVERDUE.value,
                title=f"Tarea vencida: {task.title}",
                body=(
                    f"La tarea vencio el {task.due_at.isoformat() if task.due_at else 'sin fecha'}."
                ),
                priority=NotificationPriority.HIGH.value,
                resource_type="task",
                resource_id=task.id,
                deduplication_key=f"task-overdue:{task.id}",
            )
            count += 1
        return count
