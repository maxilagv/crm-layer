from django.conf import settings
from django.db import models
from django.utils import timezone

from crm.core.models import BaseModel

from .domain.enums import (
    DigestStatus,
    NotificationChannelStatus,
    NotificationChannelType,
    NotificationDeliveryStatus,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)


class Notification(BaseModel):
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    type = models.CharField(max_length=32, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    priority = models.CharField(
        max_length=16, choices=NotificationPriority.choices, default=NotificationPriority.MEDIUM
    )
    status = models.CharField(
        max_length=16, choices=NotificationStatus.choices, default=NotificationStatus.UNREAD
    )
    resource_type = models.CharField(max_length=64, blank=True)
    resource_id = models.UUIDField(null=True, blank=True)
    deduplication_key = models.CharField(max_length=255, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_notification"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "deduplication_key"],
                condition=models.Q(deduplication_key__gt=""),
                name="uniq_notification_org_dedupe",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "recipient_user"]),
            models.Index(fields=["organization_id", "type"]),
            models.Index(fields=["organization_id", "priority"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["organization_id", "resource_type", "resource_id"]),
        ]

    def mark_read(self) -> None:
        if self.status == NotificationStatus.READ:
            return
        self.status = NotificationStatus.READ
        self.read_at = timezone.now()
        self.save(update_fields=["status", "read_at", "updated_at"])

    def __str__(self) -> str:
        return self.title


class NotificationDelivery(BaseModel):
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="deliveries"
    )
    channel = models.CharField(
        max_length=16,
        choices=NotificationChannelType.choices,
        default=NotificationChannelType.DASHBOARD,
    )
    status = models.CharField(
        max_length=16,
        choices=NotificationDeliveryStatus.choices,
        default=NotificationDeliveryStatus.PENDING,
    )
    external_message_id = models.CharField(max_length=255, blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        db_table = "notifications_delivery"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "idempotency_key"],
                condition=models.Q(idempotency_key__gt=""),
                name="uniq_notification_delivery_org_idempotency",
            ),
            models.UniqueConstraint(
                fields=["notification", "channel"],
                condition=models.Q(status=NotificationDeliveryStatus.SENT),
                name="uniq_sent_delivery_notification_channel",
            ),
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "notification"]),
            models.Index(fields=["organization_id", "channel"]),
            models.Index(fields=["organization_id", "status"]),
            models.Index(fields=["external_message_id"]),
        ]

    def __str__(self) -> str:
        return f"delivery:{self.notification_id}:{self.channel}:{self.status}"


class NotificationChannel(BaseModel):
    channel = models.CharField(max_length=16, choices=NotificationChannelType.choices)
    name = models.CharField(max_length=120)
    status = models.CharField(
        max_length=16,
        choices=NotificationChannelStatus.choices,
        default=NotificationChannelStatus.ACTIVE,
    )
    is_default = models.BooleanField(default=False)
    configuration = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "notifications_channel"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "channel", "name"],
                name="uniq_notification_channel_org_channel_name",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "channel", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.channel}:{self.name}"


class NotificationPreference(BaseModel):
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    notification_type = models.CharField(
        max_length=32, choices=NotificationType.choices, blank=True
    )
    channel = models.CharField(
        max_length=16,
        choices=NotificationChannelType.choices,
        default=NotificationChannelType.WHATSAPP,
    )
    is_enabled = models.BooleanField(default=True)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    max_per_hour = models.PositiveSmallIntegerField(default=5)
    digest_only = models.BooleanField(default=False)

    class Meta:
        db_table = "notifications_preference"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "recipient_user", "notification_type", "channel"],
                name="uniq_notification_preference_org_user_type_channel",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["organization_id", "recipient_user"]),
            models.Index(fields=["organization_id", "channel"]),
        ]

    def __str__(self) -> str:
        return f"preference:{self.recipient_user_id}:{self.notification_type}:{self.channel}"


class NotificationDigest(BaseModel):
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_digests",
    )
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    status = models.CharField(
        max_length=16, choices=DigestStatus.choices, default=DigestStatus.PENDING
    )
    title = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    notification_count = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_digest"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "recipient_user", "period_start", "period_end"],
                name="uniq_notification_digest_org_user_period",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["created_at"]),
            models.Index(
                fields=["organization_id", "recipient_user", "period_start", "period_end"]
            ),
            models.Index(fields=["organization_id", "status"]),
        ]

    def __str__(self) -> str:
        return self.title or f"digest:{self.period_start}:{self.period_end}"
