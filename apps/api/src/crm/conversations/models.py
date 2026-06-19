"""Conversations domain models.

A conversation always belongs to one organization and one contact. Messages
always belong to a conversation and a contact. ``organization_id`` is
denormalized onto every row for fast tenant-scoped queries. Joinable relations
(contact, assigned_user, conversation) are real FKs so the inbox can
``select_related`` without N+1.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from crm.contacts.models import Contact
from crm.core.models import BaseModel

from .constants import (
    IMPORTANCE_MAX,
    IMPORTANCE_MIN,
    Channel,
    ConversationMode,
    ConversationStatus,
    MemoryType,
    MessageDirection,
    MessageStatus,
    MessageType,
    SummaryType,
)


class Conversation(BaseModel):
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="conversations")
    channel = models.CharField(max_length=32, choices=Channel.choices)
    status = models.CharField(
        max_length=32, choices=ConversationStatus.choices, default=ConversationStatus.OPEN
    )
    # Static default; the operative mode is computed by ConversationRouter on create.
    mode = models.CharField(
        max_length=32, choices=ConversationMode.choices, default=ConversationMode.MANUAL
    )
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_conversations",
    )
    ai_enabled = models.BooleanField(default=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_inbound_at = models.DateTimeField(null=True, blank=True)
    last_outbound_at = models.DateTimeField(null=True, blank=True)
    summary = models.TextField(blank=True)

    class Meta:
        db_table = "conversations_conversation"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "status", "mode"]),
            models.Index(fields=["organization_id", "last_message_at"]),
            models.Index(fields=["organization_id", "contact", "channel"]),
            models.Index(fields=["organization_id", "assigned_user"]),
        ]

    def __str__(self) -> str:
        return f"conversation:{self.id}"


class Message(BaseModel):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="messages")
    direction = models.CharField(max_length=16, choices=MessageDirection.choices)
    message_type = models.CharField(
        max_length=32, choices=MessageType.choices, default=MessageType.TEXT
    )
    body = models.TextField(blank=True)
    normalized_text = models.TextField(blank=True)
    external_message_id = models.CharField(max_length=255, blank=True)
    external_timestamp = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=MessageStatus.choices, default=MessageStatus.RECEIVED
    )
    # Raw provider payload: persisted for audit/debug, never exposed via public API.
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "conversations_message"
        constraints = [
            # Deduplicate external messages within a tenant; empty ids (internal/
            # outbound messages without a provider id) are exempt via the condition.
            models.UniqueConstraint(
                fields=["organization_id", "external_message_id"],
                condition=models.Q(external_message_id__gt=""),
                name="uniq_message_org_external_id",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "conversation", "created_at"]),
            models.Index(fields=["organization_id", "contact", "created_at"]),
            models.Index(fields=["organization_id", "external_message_id"]),
            models.Index(fields=["organization_id", "direction"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["conversation", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"message:{self.id}"


class MessageAttachment(BaseModel):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    # media_asset_id stays null until the media module exists (future phase).
    media_asset_id = models.UUIDField(null=True, blank=True)
    external_media_id = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    size_bytes = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "conversations_message_attachment"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["message"]),
            models.Index(fields=["organization_id", "external_media_id"]),
        ]

    def __str__(self) -> str:
        return self.file_name or f"attachment:{self.id}"


class ConversationSummary(BaseModel):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="summaries"
    )
    summary = models.TextField()
    summary_type = models.CharField(
        max_length=32, choices=SummaryType.choices, default=SummaryType.SHORT
    )
    # Range of messages covered (UUIDs, not FKs: range markers, not relations).
    source_message_from_id = models.UUIDField(null=True, blank=True)
    source_message_to_id = models.UUIDField(null=True, blank=True)
    # Populated by the AI module in a later phase.
    created_by_ai_run_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "conversations_conversation_summary"
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["organization_id", "summary_type"]),
        ]

    def __str__(self) -> str:
        return f"summary:{self.conversation_id}:{self.summary_type}"


class ConversationMemory(BaseModel):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="memories"
    )
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="memories")
    memory_type = models.CharField(max_length=32, choices=MemoryType.choices)
    content = models.TextField()
    importance = models.PositiveSmallIntegerField(
        default=IMPORTANCE_MIN,
        validators=[MinValueValidator(IMPORTANCE_MIN), MaxValueValidator(IMPORTANCE_MAX)],
    )
    # Vector reference, populated when embeddings exist (future phase).
    embedding_id = models.UUIDField(null=True, blank=True)
    source_message_id = models.UUIDField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "conversations_conversation_memory"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(importance__gte=IMPORTANCE_MIN, importance__lte=IMPORTANCE_MAX),
                name="ck_conversation_memory_importance_range",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["organization_id", "contact", "memory_type"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"memory:{self.conversation_id}:{self.memory_type}"
