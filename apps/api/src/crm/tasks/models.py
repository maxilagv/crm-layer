from django.conf import settings
from django.db import models
from django.utils import timezone

from crm.clients.models import Client
from crm.contacts.models import Contact
from crm.conversations.models import Conversation, Message
from crm.core.models import BaseModel
from crm.leads.models import Lead
from crm.support.models import SupportTicket

from .domain.enums import (
    ACTIVE_TASK_STATUSES,
    TaskAuthorType,
    TaskCommandStatus,
    TaskCommandType,
    TaskPriority,
    TaskReminderChannel,
    TaskReminderStatus,
    TaskSourceType,
    TaskStatus,
)


class Task(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=32, choices=TaskStatus.choices, default=TaskStatus.PENDING)
    priority = models.CharField(
        max_length=16, choices=TaskPriority.choices, default=TaskPriority.MEDIUM
    )
    source_type = models.CharField(
        max_length=32, choices=TaskSourceType.choices, default=TaskSourceType.MANUAL
    )
    source_id = models.UUIDField(null=True, blank=True)
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks"
    )
    lead = models.ForeignKey(
        Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks"
    )
    client = models.ForeignKey(
        Client, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks"
    )
    ticket = models.ForeignKey(
        SupportTicket, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks"
    )
    conversation = models.ForeignKey(
        Conversation, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "tasks_task"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "idempotency_key"],
                condition=models.Q(idempotency_key__gt=""),
                name="uniq_task_org_idempotency_key",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status=TaskStatus.COMPLETED, completed_at__isnull=False)
                    | ~models.Q(status=TaskStatus.COMPLETED)
                ),
                name="ck_task_completed_requires_completed_at",
            ),
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["organization_id", "priority"]),
            models.Index(fields=["organization_id", "assigned_to"]),
            models.Index(fields=["organization_id", "due_at"]),
            models.Index(fields=["organization_id", "contact"]),
            models.Index(fields=["organization_id", "lead"]),
            models.Index(fields=["organization_id", "client"]),
            models.Index(fields=["organization_id", "ticket"]),
            models.Index(fields=["organization_id", "conversation"]),
            models.Index(fields=["organization_id", "source_type"]),
            models.Index(fields=["organization_id", "idempotency_key"]),
        ]

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_TASK_STATUSES

    def __str__(self) -> str:
        return self.title


class TaskReminder(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="reminders")
    remind_at = models.DateTimeField(db_index=True)
    channel = models.CharField(
        max_length=16, choices=TaskReminderChannel.choices, default=TaskReminderChannel.WHATSAPP
    )
    status = models.CharField(
        max_length=16, choices=TaskReminderStatus.choices, default=TaskReminderStatus.PENDING
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    snoozed_until = models.DateTimeField(null=True, blank=True)
    notification_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "tasks_task_reminder"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "task", "channel", "remind_at"],
                condition=models.Q(
                    status__in=[TaskReminderStatus.PENDING, TaskReminderStatus.QUEUED]
                ),
                name="uniq_pending_task_reminder",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "task"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["organization_id", "remind_at"]),
            models.Index(fields=["organization_id", "channel"]),
        ]

    def mark_sent(self, *, notification_id=None) -> None:
        self.status = TaskReminderStatus.SENT
        self.sent_at = timezone.now()
        if notification_id:
            self.notification_id = notification_id
        self.save(update_fields=["status", "sent_at", "notification_id", "updated_at"])

    def __str__(self) -> str:
        return f"reminder:{self.task_id}:{self.remind_at}"


class TaskComment(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author_type = models.CharField(
        max_length=16, choices=TaskAuthorType.choices, default=TaskAuthorType.USER
    )
    author_id = models.UUIDField(null=True, blank=True)
    body = models.TextField()

    class Meta:
        db_table = "tasks_task_comment"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "task", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"comment:{self.task_id}"


class TaskStatusHistory(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32, choices=TaskStatus.choices)
    reason = models.TextField(blank=True)
    changed_by_id = models.UUIDField(null=True, blank=True)
    changed_by_type = models.CharField(
        max_length=16, choices=TaskAuthorType.choices, default=TaskAuthorType.SYSTEM
    )

    class Meta:
        db_table = "tasks_task_status_history"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "task", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.task_id}:{self.from_status}->{self.to_status}"


class TaskCommand(BaseModel):
    task = models.ForeignKey(
        Task, on_delete=models.SET_NULL, null=True, blank=True, related_name="commands"
    )
    message = models.ForeignKey(
        Message, on_delete=models.SET_NULL, null=True, blank=True, related_name="task_commands"
    )
    raw_command = models.TextField()
    command_type = models.CharField(
        max_length=16, choices=TaskCommandType.choices, default=TaskCommandType.UNKNOWN
    )
    parsed_command = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16, choices=TaskCommandStatus.choices, default=TaskCommandStatus.RECEIVED
    )
    result = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "tasks_task_command"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "message"],
                condition=models.Q(message__isnull=False),
                name="uniq_task_command_org_message",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "task"]),
            models.Index(fields=["organization_id", "message"]),
            models.Index(fields=["organization_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"command:{self.command_type}:{self.status}"


class TaskSource(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="sources")
    source_type = models.CharField(
        max_length=32, choices=TaskSourceType.choices, default=TaskSourceType.MANUAL
    )
    source_id = models.UUIDField(null=True, blank=True)
    source_message = models.ForeignKey(
        Message, on_delete=models.SET_NULL, null=True, blank=True, related_name="task_sources"
    )
    ai_run_id = models.UUIDField(null=True, blank=True)
    normalized_title = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "tasks_task_source"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "source_message", "normalized_title"],
                condition=models.Q(
                    source_message__isnull=False,
                    normalized_title__gt="",
                ),
                name="uniq_task_source_message_title",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "source_type", "source_id"]),
            models.Index(fields=["organization_id", "source_message"]),
            models.Index(fields=["organization_id", "task"]),
        ]

    def __str__(self) -> str:
        return f"source:{self.task_id}:{self.source_type}"
