from django.db import models


class NotificationType(models.TextChoices):
    HOT_LEAD = "hot_lead", "Hot lead"
    CALL_REQUESTED = "call_requested", "Call requested"
    URGENT_TICKET = "urgent_ticket", "Urgent ticket"
    TASK_DUE = "task_due", "Task due"
    TASK_OVERDUE = "task_overdue", "Task overdue"
    AI_FAILURE = "ai_failure", "AI failure"
    WHATSAPP_FAILURE = "whatsapp_failure", "WhatsApp failure"
    SYSTEM_ALERT = "system_alert", "System alert"
    DAILY_DIGEST = "daily_digest", "Daily digest"


class NotificationPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class NotificationStatus(models.TextChoices):
    UNREAD = "unread", "Unread"
    READ = "read", "Read"
    ARCHIVED = "archived", "Archived"
    CANCELLED = "cancelled", "Cancelled"


class NotificationChannelType(models.TextChoices):
    WHATSAPP = "whatsapp", "WhatsApp"
    DASHBOARD = "dashboard", "Dashboard"
    EMAIL = "email", "Email"
    SYSTEM = "system", "System"


class NotificationChannelStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    DISABLED = "disabled", "Disabled"


class NotificationDeliveryStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"
    SUPPRESSED = "suppressed", "Suppressed"


class DigestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    BUILT = "built", "Built"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"
