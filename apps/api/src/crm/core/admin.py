from django.contrib import admin

from .models import IdempotencyKey, OutboxEvent


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ("scope", "key", "organization_id", "status", "expires_at", "created_at")
    list_filter = ("scope", "status")
    search_fields = ("key", "request_hash")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "organization_id", "status", "attempts", "available_at")
    list_filter = ("event_type", "status")
    search_fields = ("event_type", "error_message")
    readonly_fields = ("id", "created_at", "updated_at")
