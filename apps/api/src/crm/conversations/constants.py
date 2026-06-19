"""Centralized choices and event names for the conversations module."""

from django.db import models


class Channel(models.TextChoices):
    WHATSAPP = "whatsapp", "WhatsApp"
    EMAIL = "email", "Email"
    DASHBOARD = "dashboard", "Dashboard"
    SYSTEM = "system", "System"


class ConversationStatus(models.TextChoices):
    OPEN = "open", "Open"
    PENDING = "pending", "Pending"
    CLOSED = "closed", "Closed"
    ARCHIVED = "archived", "Archived"


class ConversationMode(models.TextChoices):
    SALES_AI = "sales_ai", "Sales AI"
    SUPPORT_AI = "support_ai", "Support AI"
    INTERNAL_ASSISTANT = "internal_assistant", "Internal assistant"
    MANUAL = "manual", "Manual"
    PAUSED = "paused", "Paused"
    BLOCKED = "blocked", "Blocked"


class MessageDirection(models.TextChoices):
    INBOUND = "inbound", "Inbound"
    OUTBOUND = "outbound", "Outbound"
    INTERNAL = "internal", "Internal"
    SYSTEM = "system", "System"


class MessageType(models.TextChoices):
    TEXT = "text", "Text"
    AUDIO = "audio", "Audio"
    IMAGE = "image", "Image"
    DOCUMENT = "document", "Document"
    VIDEO = "video", "Video"
    STICKER = "sticker", "Sticker"
    LOCATION = "location", "Location"
    CONTACT_CARD = "contact_card", "Contact card"
    SYSTEM = "system", "System"


class MessageStatus(models.TextChoices):
    RECEIVED = "received", "Received"
    PROCESSED = "processed", "Processed"
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    READ = "read", "Read"
    FAILED = "failed", "Failed"
    IGNORED = "ignored", "Ignored"


class SummaryType(models.TextChoices):
    SHORT = "short", "Short"
    TECHNICAL = "technical", "Technical"
    SALES = "sales", "Sales"
    SUPPORT = "support", "Support"
    DAILY = "daily", "Daily"
    HANDOFF = "handoff", "Handoff"


class MemoryType(models.TextChoices):
    PREFERENCE = "preference", "Preference"
    PAIN_POINT = "pain_point", "Pain point"
    TECHNICAL_CONTEXT = "technical_context", "Technical context"
    COMMERCIAL_CONTEXT = "commercial_context", "Commercial context"
    SUPPORT_CONTEXT = "support_context", "Support context"
    OBJECTION = "objection", "Objection"
    COMMITMENT = "commitment", "Commitment"


# Statuses where a conversation can still be reused by the resolver.
ACTIVE_STATUSES = (ConversationStatus.OPEN, ConversationStatus.PENDING)

# Memory importance is an integer scale from 1 (low) to 5 (critical).
IMPORTANCE_MIN = 1
IMPORTANCE_MAX = 5

# Versioned internal event types (emitted via the outbox).
EVENT_CONVERSATION_CREATED = "conversation.created.v1"
EVENT_MODE_CHANGED = "conversation.mode_changed.v1"
EVENT_MESSAGE_RECEIVED = "conversation.message_received.v1"
EVENT_MESSAGE_SENT = "conversation.message_sent.v1"
EVENT_HANDOFF_REQUESTED = "conversation.handoff_requested.v1"
