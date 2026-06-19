from crm.tasks.domain.enums import TaskStatus

from .task_completion import TaskCompletionService
from .task_source_resolver import TaskSourceResolver


class TaskUpdater:
    @staticmethod
    def update(*, organization, task, data: dict, actor=None, request=None):
        status = data.pop("status", None)
        if status and status != task.status:
            if status == TaskStatus.COMPLETED.value:
                task = TaskCompletionService.complete(task=task, actor=actor, request=request)
            elif status == TaskStatus.CANCELLED.value:
                task = TaskCompletionService.cancel(task=task, actor=actor, request=request)
            elif status == TaskStatus.PENDING.value:
                task = TaskCompletionService.mark_pending(task=task, actor=actor, request=request)
            else:
                old_status = task.status
                task.status = status
                task.updated_by_id = getattr(actor, "id", None)
                task.save(update_fields=["status", "updated_by_id", "updated_at"])
                from crm.tasks.models import TaskStatusHistory

                TaskStatusHistory.objects.create(
                    organization_id=task.organization_id,
                    task=task,
                    from_status=old_status,
                    to_status=status,
                    reason="task_updated",
                    changed_by_id=getattr(actor, "id", None),
                    changed_by_type="user" if actor else "system",
                )
        relation_keys = {
            "contact_id",
            "lead_id",
            "client_id",
            "ticket_id",
            "conversation_id",
        }
        if relation_keys & set(data):
            resolved = TaskSourceResolver.resolve(
                organization=organization,
                contact_id=data.pop("contact_id", None),
                lead_id=data.pop("lead_id", None),
                client_id=data.pop("client_id", None),
                ticket_id=data.pop("ticket_id", None),
                conversation_id=data.pop("conversation_id", None),
            )
            task.contact = resolved.contact
            task.lead = resolved.lead
            task.client = resolved.client
            task.ticket = resolved.ticket
            task.conversation = resolved.conversation
            task.save(
                update_fields=["contact", "lead", "client", "ticket", "conversation", "updated_at"]
            )
        mutable = ["title", "description", "priority", "due_at", "assigned_to", "metadata"]
        changed = []
        for field in mutable:
            if field in data:
                setattr(task, field, data[field])
                changed.append(field)
        if changed:
            task.updated_by_id = getattr(actor, "id", None)
            task.save(update_fields=[*changed, "updated_by_id", "updated_at"])
        return task
