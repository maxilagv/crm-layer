"""Support domain models.

A ticket belongs to an organization and a contact; it links to a client (when
the contact is a client), a conversation and a source message. ``source_message_id``
is unique-when-present so the same inbound message/audio never creates two
tickets. The status timeline lives in ``SupportTicketEvent``.
"""

from django.conf import settings
from django.db import models

from crm.clients.models import Client
from crm.contacts.models import Contact
from crm.core.models import BaseModel
from crm.media.models import MediaAsset

from .domain.enums import (
    ActorType,
    AttachmentType,
    CommentVisibility,
    KnownIssueSeverity,
    KnownIssueStatus,
    ResolvedByType,
    TicketCategory,
    TicketEventType,
    TicketPriority,
    TicketStatus,
)


class SupportTicket(BaseModel):
    client = models.ForeignKey(
        Client, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets"
    )
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="support_tickets")
    conversation_id = models.UUIDField(null=True, blank=True)
    source_message_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN
    )
    priority = models.CharField(
        max_length=12, choices=TicketPriority.choices, default=TicketPriority.MEDIUM
    )
    category = models.CharField(
        max_length=20, choices=TicketCategory.choices, default=TicketCategory.UNKNOWN
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    technical_summary = models.TextField(blank=True)
    ai_summary = models.TextField(blank=True)
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )
    due_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "support_ticket"
        constraints = [
            # One ticket per source message (deduplicate AI/inbound creation).
            models.UniqueConstraint(
                fields=["organization_id", "source_message_id"],
                condition=models.Q(source_message_id__isnull=False, deleted_at__isnull=True),
                name="uniq_ticket_per_source_message",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["organization_id", "priority"]),
            models.Index(fields=["organization_id", "category"]),
            models.Index(fields=["organization_id", "client"]),
            models.Index(fields=["organization_id", "contact"]),
            models.Index(fields=["organization_id", "assigned_user"]),
            models.Index(fields=["organization_id", "due_at"]),
            models.Index(fields=["source_message_id"]),
        ]

    def __str__(self) -> str:
        return self.title


class SupportTicketEvent(BaseModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=32, choices=TicketEventType.choices)
    actor_type = models.CharField(
        max_length=16, choices=ActorType.choices, default=ActorType.SYSTEM
    )
    actor_id = models.UUIDField(null=True, blank=True)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "support_ticket_event"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["organization_id", "ticket", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.ticket_id}:{self.event_type}"


class SupportTicketComment(BaseModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="comments")
    author_type = models.CharField(max_length=16, choices=ActorType.choices, default=ActorType.USER)
    author_id = models.UUIDField(null=True, blank=True)
    body = models.TextField()
    visibility = models.CharField(
        max_length=12, choices=CommentVisibility.choices, default=CommentVisibility.INTERNAL
    )

    class Meta:
        db_table = "support_ticket_comment"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["ticket", "created_at"]),
            models.Index(fields=["organization_id", "visibility"]),
        ]

    def __str__(self) -> str:
        return f"comment:{self.ticket_id}"


class SupportTicketAttachment(BaseModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="attachments")
    media_asset = models.ForeignKey(
        MediaAsset, on_delete=models.PROTECT, related_name="support_attachments"
    )
    source_message_id = models.UUIDField(null=True, blank=True)
    attachment_type = models.CharField(
        max_length=20, choices=AttachmentType.choices, default=AttachmentType.OTHER
    )

    class Meta:
        db_table = "support_ticket_attachment"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["ticket"]),
            models.Index(fields=["organization_id", "attachment_type"]),
        ]

    def __str__(self) -> str:
        return f"attachment:{self.ticket_id}:{self.attachment_type}"


class SupportKnownIssue(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20, choices=TicketCategory.choices, default=TicketCategory.UNKNOWN
    )
    status = models.CharField(
        max_length=16, choices=KnownIssueStatus.choices, default=KnownIssueStatus.ACTIVE
    )
    severity = models.CharField(
        max_length=12, choices=KnownIssueSeverity.choices, default=KnownIssueSeverity.MEDIUM
    )
    matching_keywords = models.JSONField(default=list, blank=True)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        db_table = "support_known_issue"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status", "category"]),
        ]

    def __str__(self) -> str:
        return self.title


class SupportResolution(BaseModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="resolutions")
    summary = models.TextField()
    root_cause = models.TextField(blank=True)
    resolution_steps = models.TextField(blank=True)
    resolved_by_id = models.UUIDField(null=True, blank=True)
    resolved_by_type = models.CharField(
        max_length=16, choices=ResolvedByType.choices, default=ResolvedByType.USER
    )
    ai_run_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "support_resolution"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["ticket", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"resolution:{self.ticket_id}"
