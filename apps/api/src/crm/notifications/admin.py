from django.contrib import admin

from .models import (
    Notification,
    NotificationChannel,
    NotificationDelivery,
    NotificationDigest,
    NotificationPreference,
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "organization_id", "recipient_user", "type", "priority", "status")
    list_filter = ("type", "priority", "status")
    search_fields = ("title", "body")
    readonly_fields = (
        "id",
        "organization_id",
        "deduplication_key",
        "read_at",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ("notification", "organization_id", "channel", "status", "attempts", "sent_at")
    list_filter = ("channel", "status")
    search_fields = ("notification__title", "external_message_id")
    readonly_fields = (
        "id",
        "organization_id",
        "external_message_id",
        "last_error",
        "created_at",
        "updated_at",
    )


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ("name", "organization_id", "channel", "status", "is_default")
    list_filter = ("channel", "status", "is_default")
    search_fields = ("name",)
    readonly_fields = ("id", "organization_id", "created_at", "updated_at")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "recipient_user",
        "organization_id",
        "notification_type",
        "channel",
        "is_enabled",
    )
    list_filter = ("channel", "is_enabled", "digest_only")
    search_fields = ("recipient_user__email",)
    readonly_fields = ("id", "organization_id", "created_at", "updated_at")


@admin.register(NotificationDigest)
class NotificationDigestAdmin(admin.ModelAdmin):
    list_display = ("title", "organization_id", "recipient_user", "status", "notification_count")
    list_filter = ("status",)
    search_fields = ("title", "body")
    readonly_fields = ("id", "organization_id", "body", "created_at", "updated_at")
    date_hierarchy = "period_start"
