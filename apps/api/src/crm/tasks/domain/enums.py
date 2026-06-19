from django.db import models


class TaskStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In progress"
    WAITING = "waiting", "Waiting"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    OVERDUE = "overdue", "Overdue"
    SNOOZED = "snoozed", "Snoozed"


class TaskPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class TaskSourceType(models.TextChoices):
    MANUAL = "manual", "Manual"
    CONVERSATION = "conversation", "Conversation"
    LEAD = "lead", "Lead"
    TICKET = "ticket", "Ticket"
    AI_EXTRACTED = "ai_extracted", "AI extracted"
    AUTOMATION = "automation", "Automation"
    SYSTEM = "system", "System"


class TaskReminderChannel(models.TextChoices):
    WHATSAPP = "whatsapp", "WhatsApp"
    DASHBOARD = "dashboard", "Dashboard"
    EMAIL = "email", "Email"
    SYSTEM = "system", "System"


class TaskReminderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    SNOOZED = "snoozed", "Snoozed"
    CANCELLED = "cancelled", "Cancelled"
    FAILED = "failed", "Failed"
    EXPIRED = "expired", "Expired"


class TaskAuthorType(models.TextChoices):
    USER = "user", "User"
    AI_AGENT = "ai_agent", "AI agent"
    SYSTEM = "system", "System"
    WORKER = "worker", "Worker"


class TaskCommandType(models.TextChoices):
    COMPLETE = "complete", "Complete"
    PENDING = "pending", "Pending"
    SNOOZE = "snooze", "Snooze"
    CANCEL = "cancel", "Cancel"
    DETAIL = "detail", "Detail"
    UNKNOWN = "unknown", "Unknown"


class TaskCommandStatus(models.TextChoices):
    RECEIVED = "received", "Received"
    PROCESSED = "processed", "Processed"
    REJECTED = "rejected", "Rejected"
    FAILED = "failed", "Failed"


ACTIVE_TASK_STATUSES = (
    TaskStatus.PENDING.value,
    TaskStatus.IN_PROGRESS.value,
    TaskStatus.WAITING.value,
    TaskStatus.OVERDUE.value,
    TaskStatus.SNOOZED.value,
)

TERMINAL_TASK_STATUSES = (
    TaskStatus.COMPLETED.value,
    TaskStatus.CANCELLED.value,
)
