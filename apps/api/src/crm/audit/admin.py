from django.contrib import admin

from .models import (
    AuditAIDecision,
    AuditDataAccessLog,
    AuditEvent,
    AuditExternalRequest,
    AuditLog,
    AuditSecurityEvent,
)


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("action", "actor_type", "resource_type", "resource_id", "created_at")
    list_filter = ("action", "actor_type", "resource_type")
    search_fields = ("action", "resource_id", "request_id")
    readonly_fields = ("id", "created_at", "updated_at")


class ReadOnlyAuditAdmin(admin.ModelAdmin):
    readonly_fields = (
        "id",
        "organization_id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by_id",
        "updated_by_id",
        "metadata",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD"} and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyAuditAdmin):
    list_display = ("action", "actor_type", "resource_type", "resource_id", "created_at")
    list_filter = ("action", "actor_type", "resource_type")
    search_fields = ("action", "resource_id", "request_id", "correlation_id")


@admin.register(AuditDataAccessLog)
class AuditDataAccessLogAdmin(ReadOnlyAuditAdmin):
    list_display = ("access_type", "actor_type", "resource_type", "resource_id", "created_at")
    list_filter = ("access_type", "actor_type", "resource_type")
    search_fields = ("resource_id", "request_id", "correlation_id")


@admin.register(AuditSecurityEvent)
class AuditSecurityEventAdmin(ReadOnlyAuditAdmin):
    list_display = ("event_type", "severity", "actor_type", "created_at")
    list_filter = ("event_type", "severity", "actor_type")
    search_fields = ("event_type", "request_id", "correlation_id", "description")


@admin.register(AuditAIDecision)
class AuditAIDecisionAdmin(ReadOnlyAuditAdmin):
    list_display = ("decision_type", "purpose", "provider", "model", "ai_run_id", "created_at")
    list_filter = ("decision_type", "purpose", "provider", "model")
    search_fields = ("ai_run_id", "request_id", "correlation_id")


@admin.register(AuditExternalRequest)
class AuditExternalRequestAdmin(ReadOnlyAuditAdmin):
    list_display = ("provider", "operation", "status_code", "success", "created_at")
    list_filter = ("provider", "success", "error_code")
    search_fields = ("provider", "operation", "url_host", "request_id", "correlation_id")
