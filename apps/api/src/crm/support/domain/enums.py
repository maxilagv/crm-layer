"""Centralized choices for the support module."""

from django.db import models


class TicketStatus(models.TextChoices):
    OPEN = "open", "Open"
    WAITING_CLIENT = "waiting_client", "Waiting client"
    TRIAGED = "triaged", "Triaged"
    IN_PROGRESS = "in_progress", "In progress"
    BLOCKED = "blocked", "Blocked"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"
    CANCELLED = "cancelled", "Cancelled"


class TicketPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"
    CRITICAL = "critical", "Critical"


class TicketCategory(models.TextChoices):
    BUG = "bug", "Bug"
    ACCESS = "access", "Access"
    BILLING = "billing", "Billing"
    FEATURE_REQUEST = "feature_request", "Feature request"
    INTEGRATION = "integration", "Integration"
    PERFORMANCE = "performance", "Performance"
    DATA_ISSUE = "data_issue", "Data issue"
    UNKNOWN = "unknown", "Unknown"


class TicketEventType(models.TextChoices):
    CREATED = "created", "Created"
    STATUS_CHANGED = "status_changed", "Status changed"
    ASSIGNED = "assigned", "Assigned"
    COMMENT_ADDED = "comment_added", "Comment added"
    ATTACHMENT_ADDED = "attachment_added", "Attachment added"
    TRIAGED = "triaged", "Triaged"
    PRIORITY_CHANGED = "priority_changed", "Priority changed"
    RESOLVED = "resolved", "Resolved"
    REOPENED = "reopened", "Reopened"
    CLOSED = "closed", "Closed"
    AI_SUMMARY_GENERATED = "ai_summary_generated", "AI summary generated"
    OWNER_NOTIFIED = "owner_notified", "Owner notified"


class ActorType(models.TextChoices):
    USER = "user", "User"
    AI_AGENT = "ai_agent", "AI agent"
    SYSTEM = "system", "System"
    WORKER = "worker", "Worker"
    WEBHOOK = "webhook", "Webhook"
    CLIENT = "client", "Client"


class CommentVisibility(models.TextChoices):
    INTERNAL = "internal", "Internal"
    CLIENT = "client", "Client"


class AttachmentType(models.TextChoices):
    AUDIO = "audio", "Audio"
    IMAGE = "image", "Image"
    DOCUMENT = "document", "Document"
    LOG = "log", "Log"
    SCREENSHOT = "screenshot", "Screenshot"
    GENERATED_ASSET = "generated_asset", "Generated asset"
    OTHER = "other", "Other"


class KnownIssueStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    MONITORING = "monitoring", "Monitoring"
    RESOLVED = "resolved", "Resolved"
    ARCHIVED = "archived", "Archived"


class KnownIssueSeverity(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class ResolvedByType(models.TextChoices):
    USER = "user", "User"
    AI_AGENT = "ai_agent", "AI agent"
    SYSTEM = "system", "System"


# Priorities that always require notifying the owner.
OWNER_NOTIFY_PRIORITIES = (TicketPriority.URGENT, TicketPriority.CRITICAL)

# Priority ordering for max() comparisons.
PRIORITY_ORDER = {
    TicketPriority.LOW.value: 0,
    TicketPriority.MEDIUM.value: 1,
    TicketPriority.HIGH.value: 2,
    TicketPriority.URGENT.value: 3,
    TicketPriority.CRITICAL.value: 4,
}


def max_priority(*priorities: str) -> str:
    present = [p for p in priorities if p in PRIORITY_ORDER]
    if not present:
        return TicketPriority.MEDIUM.value
    return max(present, key=lambda p: PRIORITY_ORDER[p])
