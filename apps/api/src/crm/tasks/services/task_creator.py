from django.db import IntegrityError, transaction
from django.utils import timezone

from crm.audit.services import audit_event_create
from crm.core.services.outbox import create_outbox_event
from crm.tasks.domain import events
from crm.tasks.domain.enums import (
    TaskAuthorType,
    TaskPriority,
    TaskReminderChannel,
    TaskSourceType,
    TaskStatus,
)
from crm.tasks.domain.rules import clamp_priority, normalize_title
from crm.tasks.models import Task, TaskSource

from .task_deduplication import TaskDeduplicationService
from .task_scheduler import TaskScheduler
from .task_source_resolver import TaskSourceResolver


class TaskCreator:
    @staticmethod
    @transaction.atomic
    def create(
        *,
        organization,
        title: str,
        description: str = "",
        priority: str = TaskPriority.MEDIUM.value,
        due_at=None,
        source_type: str = TaskSourceType.MANUAL.value,
        source_id=None,
        contact=None,
        lead=None,
        client=None,
        ticket=None,
        conversation=None,
        source_message=None,
        assigned_to=None,
        actor=None,
        request=None,
        metadata: dict | None = None,
        idempotency_key: str = "",
        ai_run_id=None,
        schedule_reminder: bool = True,
    ):
        if not title or not title.strip():
            raise ValueError("Task title is required")
        duplicate = TaskDeduplicationService.find_duplicate(
            organization_id=organization.id,
            title=title,
            source_message=source_message,
            idempotency_key=idempotency_key,
        )
        if duplicate is not None:
            return duplicate, False

        if (
            assigned_to is not None
            and not assigned_to.memberships.filter(
                organization=organization, status="active"
            ).exists()
        ):
            raise ValueError("assigned_to must belong to the organization")

        try:
            task = Task.objects.create(
                organization_id=organization.id,
                title=title.strip()[:255],
                description=description[:4000],
                priority=clamp_priority(priority),
                source_type=source_type,
                source_id=source_id,
                contact=contact,
                lead=lead,
                client=client,
                ticket=ticket,
                conversation=conversation,
                assigned_to=assigned_to,
                due_at=due_at,
                idempotency_key=idempotency_key,
                metadata=metadata or {},
                created_by_id=getattr(actor, "id", None),
            )
        except IntegrityError:
            if idempotency_key:
                return Task.objects.get(
                    organization_id=organization.id, idempotency_key=idempotency_key
                ), False
            raise

        TaskSource.objects.create(
            organization_id=organization.id,
            task=task,
            source_type=source_type,
            source_id=source_id,
            source_message=source_message,
            ai_run_id=ai_run_id,
            normalized_title=normalize_title(title),
        )
        _record_initial_history(task=task, actor=actor)
        create_outbox_event(
            event_type=events.TASK_CREATED,
            organization_id=organization.id,
            payload={
                "task_id": str(task.id),
                "title": task.title,
                "priority": task.priority,
                "source_type": task.source_type,
            },
        )
        audit_event_create(
            event_type="task_created",
            actor=actor,
            organization=organization,
            request=request,
            resource_type="task",
            resource_id=str(task.id),
            metadata={"source_type": source_type, "priority": task.priority},
        )
        if due_at and schedule_reminder:
            remind_at = min(due_at, timezone.now()) if due_at <= timezone.now() else due_at
            TaskScheduler.schedule_reminder(
                task=task,
                remind_at=remind_at,
                channel=TaskReminderChannel.WHATSAPP.value,
                actor=actor,
            )
        return task, True

    @staticmethod
    def create_manual(
        *,
        organization,
        title: str,
        description: str = "",
        priority: str = TaskPriority.MEDIUM.value,
        due_at=None,
        contact_id=None,
        lead_id=None,
        client_id=None,
        ticket_id=None,
        conversation_id=None,
        assigned_to=None,
        actor=None,
        request=None,
        metadata: dict | None = None,
        idempotency_key: str = "",
    ):
        resolved = TaskSourceResolver.resolve(
            organization=organization,
            contact_id=contact_id,
            lead_id=lead_id,
            client_id=client_id,
            ticket_id=ticket_id,
            conversation_id=conversation_id,
        )
        return TaskCreator.create(
            organization=organization,
            title=title,
            description=description,
            priority=priority,
            due_at=due_at,
            source_type=TaskSourceType.MANUAL.value,
            contact=resolved.contact,
            lead=resolved.lead,
            client=resolved.client,
            ticket=resolved.ticket,
            conversation=resolved.conversation,
            assigned_to=assigned_to,
            actor=actor,
            request=request,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

    @staticmethod
    def create_from_candidate(
        *, organization, candidate, conversation=None, message=None, actor=None
    ):
        resolved = TaskSourceResolver.resolve(
            organization=organization,
            conversation_id=getattr(conversation, "id", None),
            source_message_id=getattr(message, "id", None) or candidate.source_message_id,
        )
        return TaskCreator.create(
            organization=organization,
            title=candidate.title,
            description=candidate.description,
            priority=candidate.priority,
            due_at=candidate.due_at,
            source_type=TaskSourceType.AI_EXTRACTED.value,
            source_id=getattr(message, "id", None),
            contact=resolved.contact,
            conversation=resolved.conversation,
            source_message=message or resolved.source_message,
            actor=actor,
            metadata={**candidate.metadata, "confidence": candidate.confidence},
            ai_run_id=candidate.ai_run_id,
            idempotency_key=(
                f"ai-task:{getattr(message, 'id', '')}:{normalize_title(candidate.title)}"
            ),
        )


def _record_initial_history(*, task, actor=None):
    from crm.tasks.models import TaskStatusHistory

    TaskStatusHistory.objects.create(
        organization_id=task.organization_id,
        task=task,
        from_status="",
        to_status=TaskStatus.PENDING.value,
        reason="task_created",
        changed_by_id=getattr(actor, "id", None),
        changed_by_type=TaskAuthorType.USER.value if actor else TaskAuthorType.SYSTEM.value,
    )
