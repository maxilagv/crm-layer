from django.contrib import admin

from .models import (
    AlertDefinition,
    AlertEvent,
    AnalyticsAICostSnapshot,
    AnalyticsDailySummary,
    AnalyticsDashboardSnapshot,
    AnalyticsEvent,
    AnalyticsFunnelSnapshot,
    AnalyticsMetricSnapshot,
)


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ("event_name", "source", "organization_id", "occurred_at")
    list_filter = ("event_name", "source")
    search_fields = ("event_name", "request_id", "correlation_id", "resource_id")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AnalyticsMetricSnapshot)
class AnalyticsMetricSnapshotAdmin(admin.ModelAdmin):
    list_display = ("date", "metric_name", "organization_id", "value")
    list_filter = ("metric_name", "date")
    search_fields = ("metric_name", "dimensions_hash")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AnalyticsDailySummary)
class AnalyticsDailySummaryAdmin(admin.ModelAdmin):
    list_display = ("date", "organization_id", "created_at")
    list_filter = ("date",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AnalyticsAICostSnapshot)
class AnalyticsAICostSnapshotAdmin(admin.ModelAdmin):
    list_display = ("date", "provider", "model", "purpose", "estimated_cost", "run_count")
    list_filter = ("date", "provider", "purpose")
    search_fields = ("provider", "model", "purpose")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AnalyticsFunnelSnapshot)
class AnalyticsFunnelSnapshotAdmin(admin.ModelAdmin):
    list_display = ("date", "organization_id", "created_at")
    list_filter = ("date",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AnalyticsDashboardSnapshot)
class AnalyticsDashboardSnapshotAdmin(admin.ModelAdmin):
    list_display = ("date", "period_start", "period_end", "organization_id")
    list_filter = ("date",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AlertDefinition)
class AlertDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "metric_name", "severity", "threshold_value", "is_enabled")
    list_filter = ("severity", "is_enabled", "metric_name")
    search_fields = ("name", "metric_name", "runbook_path")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AlertEvent)
class AlertEventAdmin(admin.ModelAdmin):
    list_display = ("name", "metric_name", "severity", "status", "opened_at")
    list_filter = ("severity", "status", "metric_name")
    search_fields = ("name", "metric_name", "fingerprint", "runbook_path")
    readonly_fields = ("id", "created_at", "updated_at", "opened_at")
