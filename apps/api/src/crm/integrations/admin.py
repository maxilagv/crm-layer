from django.contrib import admin

from .models import ExternalRequestLog


@admin.register(ExternalRequestLog)
class ExternalRequestLogAdmin(admin.ModelAdmin):
    list_display = ("provider", "operation", "status", "status_code", "created_at")
    list_filter = ("provider", "operation", "status")
    search_fields = ("provider", "operation", "request_id")
    readonly_fields = ("id", "created_at", "updated_at")
