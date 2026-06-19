from django.db import transaction
from django.utils import timezone

from crm.audit.services import audit_event_create
from crm.core.services.outbox import create_outbox_event
from crm.tasks.domain import events
from crm.tasks.domain.enums import (
    TaskAuthorType,
    TaskReminderStatus,
    TaskStatus,
)
from crm.tasks.domain.exceptions import TaskSnoozeLimitExceeded
from crm.tasks.domain.rules import MAX_SNOOZE_COUNT
from crm.tasks.models import Task, TaskStatusHistory


class TaskCompletionService:
    @staticmethod
    def complete(*, task, actor=None, request=None, reason: str = "completed"):
        return _change_status(
            task=task,
            status=TaskStatus.COMPLETED.value,
            actor=actor,
            request=request,
            reason=reason,
            completed_at=timezone.now(),
            cancel_reminders=True,
        )

    @staticmethod
    def cancel(*, task, actor=None, request=None, reason: str = "cancelled"):
        return _change_status(
            task=task,
            status=TaskStatus.CANCELLED.value,
            actor=actor,
            request=request,
            reason=reason,
            cancel_reminders=True,
        )

    @staticmethod
    def mark_pending(*, task, actor=None, request=None, reason: str = "pending"):
        return _change_status(
            task=task,
            status=TaskStatus.PENDING.value,
            actor=actor,
            request=request,
            reason=reason,
            completed_at=None,
        )

    @staticmethod
    @transaction.atomic
    def snooze(*, task, snooze_until, actor=None, request=None, reason: str = "snoozed"):
        task = Task.objects.select_for_update().get(id=task.id)
        metadata = dict(task.metadata or {})
        count = int(metadata.get("snooze_count", 0))
        if count >= MAX_SNOOZE_COUNT:
            raise TaskSnoozeLimitExceeded("Snooze limit exceeded")
        metadata["snooze_count"] = count + 1
        old_status = task.status
        task.metadata = metadata
        task.due_at = snooze_until
        task.status = TaskStatus.SNOOZED.value
        task.updated_by_id = getattr(actor, "id", None)
        task.save(update_fields=["status", "due_at", "metadata", "updated_by_id", "updated_at"])
        if old_status != TaskStatus.SNOOZED.value:
            TaskStatusHistory.objects.create(
                organization_id=task.organization_id,
                task=task,
                from_status=old_status,
                to_status=TaskStatus.SNOOZED.value,
                reason=reason[:1000],
                changed_by_id=getattr(actor, "id", None),
                changed_by_type=TaskAuthorType.USER.value if actor else TaskAuthorType.SYSTEM.value,
            )
            create_outbox_event(
                event_type=events.TASK_STATUS_CHANGED,
                organization_id=task.organization_id,
                payload={
                    "task_id": str(task.id),
                    "from_status": old_status,
                    "to_status": TaskStatus.SNOOZED.value,
                },
            )
            audit_event_create(
                event_type="task_status_changed",
                actor=actor,
                organization=_org_stub(task.organization_id),
                request=request,
                resource_type="task",
                resource_id=str(task.id),
                changes={"status": {"from": old_status, "to": TaskStatus.SNOOZED.value}},
                metadata={"reason": reason[:300]},
            )
        task.reminders.filter(status__in=["pending", "queued"]).update(
            status=TaskReminderStatus.SNOOZED.value,
            snoozed_until=snooze_until,
            updated_at=timezone.now(),
        )
        from .task_scheduler import TaskScheduler

        TaskScheduler.schedule_reminder(task=task, remind_at=snooze_until, actor=actor)
        return task


@transaction.atomic
def _change_status(
    *,
    task,
    status: str,
    actor=None,
    request=None,
    reason: str = "",
    completed_at=None,
    cancel_reminders: bool = False,
    save: bool = True,
):
    task = Task.objects.select_for_update().get(id=task.id)
    old_status = task.status
    if old_status == status:
        return task
    task.status = status
    task.completed_at = completed_at
    task.updated_by_id = getattr(actor, "id", None)
    if save:
        task.save(update_fields=["status", "completed_at", "updated_by_id", "updated_at"])
    TaskStatusHistory.objects.create(
        organization_id=task.organization_id,
        task=task,
        from_status=old_status,
        to_status=status,
        reason=reason[:1000],
        changed_by_id=getattr(actor, "id", None),
        changed_by_type=TaskAuthorType.USER.value if actor else TaskAuthorType.SYSTEM.value,
    )
    if cancel_reminders:
        task.reminders.filter(status__in=["pending", "queued"]).update(
            status=TaskReminderStatus.CANCELLED.value,
            updated_at=timezone.now(),
        )
    create_outbox_event(
        event_type=events.TASK_STATUS_CHANGED,
        organization_id=task.organization_id,
        payload={"task_id": str(task.id), "from_status": old_status, "to_status": status},
    )
    audit_event_create(
        event_type="task_status_changed",
        actor=actor,
        organization=_org_stub(task.organization_id),
        request=request,
        resource_type="task",
        resource_id=str(task.id),
        changes={"status": {"from": old_status, "to": status}},
        metadata={"reason": reason[:300]},
    )
    return task


def _org_stub(organization_id):
    class _Org:
        id = organization_id

    return _Org()
