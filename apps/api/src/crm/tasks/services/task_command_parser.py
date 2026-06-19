from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_datetime

from crm.contacts.models import ContactPhone
from crm.core.services.outbox import create_outbox_event
from crm.tasks.domain import events
from crm.tasks.domain.enums import TaskCommandStatus, TaskCommandType
from crm.tasks.domain.rules import parse_command
from crm.tasks.models import Task, TaskCommand

from .task_completion import TaskCompletionService


class TaskCommandParser:
    @staticmethod
    @transaction.atomic
    def parse_and_apply(*, organization, message, task=None, actor=None, now=None):
        if not _is_owner_message(organization=organization, message=message):
            return _create_command(
                organization=organization,
                message=message,
                task=task,
                raw_command=message.body,
                parsed={"type": TaskCommandType.UNKNOWN.value},
                status=TaskCommandStatus.REJECTED.value,
                result={"reason": "not_owner"},
            )

        parsed = parse_command(message.body, now=now)
        command = _create_command(
            organization=organization,
            message=message,
            task=task,
            raw_command=message.body,
            parsed=parsed,
        )
        if command.status == TaskCommandStatus.PROCESSED.value and command.result:
            return command
        target = task or _resolve_target_task(organization=organization, message=message)
        command.task = target
        command.command_type = parsed["type"]
        if parsed["type"] == TaskCommandType.UNKNOWN.value or target is None:
            command.status = TaskCommandStatus.REJECTED.value
            command.result = {"reason": "ambiguous_or_unknown"}
            command.save(update_fields=["task", "command_type", "status", "result", "updated_at"])
            return command
        try:
            if parsed["type"] == TaskCommandType.COMPLETE.value:
                target = TaskCompletionService.complete(
                    task=target, actor=actor, reason="owner_command"
                )
            elif parsed["type"] == TaskCommandType.PENDING.value:
                target = TaskCompletionService.mark_pending(
                    task=target, actor=actor, reason="owner_command"
                )
            elif parsed["type"] == TaskCommandType.CANCEL.value:
                target = TaskCompletionService.cancel(
                    task=target, actor=actor, reason="owner_command"
                )
            elif parsed["type"] == TaskCommandType.SNOOZE.value:
                target = TaskCompletionService.snooze(
                    task=target,
                    snooze_until=parse_datetime(parsed["snooze_until"]),
                    actor=actor,
                    reason="owner_command",
                )
            elif parsed["type"] == TaskCommandType.DETAIL.value:
                pass
        except Exception as exc:
            command.status = TaskCommandStatus.FAILED.value
            command.result = {"error": str(exc)[:500]}
            command.save(update_fields=["status", "result", "updated_at"])
            raise
        command.status = TaskCommandStatus.PROCESSED.value
        command.result = {"task_id": str(target.id), "status": target.status}
        command.save(update_fields=["task", "command_type", "status", "result", "updated_at"])
        create_outbox_event(
            event_type=events.TASK_COMMAND_PROCESSED,
            organization_id=organization.id,
            payload={"command_id": str(command.id), "task_id": str(target.id)},
        )
        return command


def _create_command(
    *, organization, message, task, raw_command: str, parsed: dict, status=None, result=None
):
    try:
        command, created = TaskCommand.objects.get_or_create(
            organization_id=organization.id,
            message=message,
            defaults={
                "task": task,
                "raw_command": raw_command[:4000],
                "command_type": parsed.get("type", TaskCommandType.UNKNOWN.value),
                "parsed_command": parsed,
                "status": status or TaskCommandStatus.RECEIVED.value,
                "result": result or {},
            },
        )
    except IntegrityError:
        command = TaskCommand.objects.get(organization_id=organization.id, message=message)
        created = False
    if not created and command.status == TaskCommandStatus.PROCESSED.value:
        return command
    return command


def _resolve_target_task(*, organization, message):
    task_id = (message.metadata or {}).get("task_id")
    if task_id:
        return Task.objects.filter(id=task_id, organization_id=organization.id).first()
    reminder_id = (message.metadata or {}).get("reminder_id")
    if reminder_id:
        return Task.objects.filter(
            organization_id=organization.id, reminders__id=reminder_id
        ).first()
    return (
        Task.objects.filter(
            organization_id=organization.id,
            assigned_to=organization.owner,
            status__in=["pending", "in_progress", "waiting", "overdue", "snoozed"],
        )
        .order_by("due_at", "-created_at")
        .first()
    )


def _is_owner_message(*, organization, message) -> bool:
    contact = message.contact
    metadata = contact.metadata or {}
    if metadata.get("is_owner") is True:
        return True
    if str(metadata.get("owner_user_id") or "") == str(organization.owner_id):
        return True
    owner_phone = getattr(organization.owner, "phone", "")
    if owner_phone:
        return ContactPhone.objects.filter(
            contact=contact,
            organization_id=organization.id,
            phone_e164=owner_phone,
        ).exists()
    return False
