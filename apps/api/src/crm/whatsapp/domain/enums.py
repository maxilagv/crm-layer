from django.db import models


class WhatsAppAccountStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    DISABLED = "disabled", "Disabled"


class WhatsAppPhoneNumberStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    DISCONNECTED = "disconnected", "Disconnected"
    DISABLED = "disabled", "Disabled"


class WebhookEventStatus(models.TextChoices):
    RECEIVED = "received", "Received"
    PROCESSING = "processing", "Processing"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"
    IGNORED = "ignored", "Ignored"
    DUPLICATE = "duplicate", "Duplicate"


class WebhookEventType(models.TextChoices):
    MESSAGES = "messages", "Messages"
    STATUSES = "statuses", "Statuses"
    UNKNOWN = "unknown", "Unknown"


class WhatsAppMessageType(models.TextChoices):
    TEXT = "text", "Text"
    AUDIO = "audio", "Audio"
    IMAGE = "image", "Image"
    DOCUMENT = "document", "Document"
    VIDEO = "video", "Video"
    STICKER = "sticker", "Sticker"
    LOCATION = "location", "Location"
    CONTACT_CARD = "contact_card", "Contact card"
    TEMPLATE = "template", "Template"
    UNSUPPORTED = "unsupported", "Unsupported"


class InboundMessageStatus(models.TextChoices):
    RECEIVED = "received", "Received"
    PROCESSED = "processed", "Processed"
    IGNORED = "ignored", "Ignored"
    FAILED = "failed", "Failed"


class OutboundMessageStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    SENDING = "sending", "Sending"
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    READ = "read", "Read"
    FAILED = "failed", "Failed"
    CANCELED = "canceled", "Canceled"


class BridgeOutboundStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"
    DEAD_LETTER = "dead_letter", "Dead letter"


class WhatsAppDeliveryStatus(models.TextChoices):
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    READ = "read", "Read"
    FAILED = "failed", "Failed"
    DELETED = "deleted", "Deleted"
    WARNING = "warning", "Warning"
    UNKNOWN = "unknown", "Unknown"


class WhatsAppTemplateCategory(models.TextChoices):
    UTILITY = "utility", "Utility"
    MARKETING = "marketing", "Marketing"
    AUTHENTICATION = "authentication", "Authentication"
    INTERNAL_REMINDER = "internal_reminder", "Internal reminder"
    FOLLOW_UP = "follow_up", "Follow-up"


class WhatsAppTemplateStatus(models.TextChoices):
    APPROVED = "approved", "Approved"
    PENDING = "pending", "Pending"
    REJECTED = "rejected", "Rejected"
    PAUSED = "paused", "Paused"
    DISABLED = "disabled", "Disabled"
    DRAFT = "draft", "Draft"


class MediaReferenceStatus(models.TextChoices):
    RECEIVED = "received", "Received"
    QUEUED = "queued", "Queued"
    DOWNLOADING = "downloading", "Downloading"
    DOWNLOADED = "downloaded", "Downloaded"
    FAILED = "failed", "Failed"
    IGNORED = "ignored", "Ignored"
