from django.contrib import admin

from .models import (
    AutomationAction,
    AutomationCondition,
    AutomationRule,
    AutomationRun,
    AutomationRunStep,
    AutomationTrigger,
)


@admin.register(AutomationRule)
class AutomationRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "organization_id", "trigger_type", "is_enabled", "priority")
    list_filter = ("trigger_type", "is_enabled")
    search_fields = ("name", "description")
    readonly_fields = ("id", "organization_id", "created_at", "updated_at")


@admin.register(AutomationTrigger)
class AutomationTriggerAdmin(admin.ModelAdmin):
    list_display = ("rule", "organization_id", "trigger_type")
    list_filter = ("trigger_type",)
    readonly_fields = ("id", "organization_id", "created_at", "updated_at")


@admin.register(AutomationCondition)
class AutomationConditionAdmin(admin.ModelAdmin):
    list_display = ("rule", "organization_id", "field_path", "operator", "order")
    list_filter = ("operator", "condition_type")
    readonly_fields = ("id", "organization_id", "created_at", "updated_at")


@admin.register(AutomationAction)
class AutomationActionAdmin(admin.ModelAdmin):
    list_display = ("rule", "organization_id", "action_type", "required_permission", "order")
    list_filter = ("action_type",)
    readonly_fields = ("id", "organization_id", "created_at", "updated_at")


@admin.register(AutomationRun)
class AutomationRunAdmin(admin.ModelAdmin):
    list_display = (
        "rule",
        "organization_id",
        "trigger_type",
        "status",
        "started_at",
        "finished_at",
    )
    list_filter = ("trigger_type", "status")
    search_fields = ("trigger_event_id", "reason")
    readonly_fields = (
        "id",
        "organization_id",
        "trigger_payload",
        "reason",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"


@admin.register(AutomationRunStep)
class AutomationRunStepAdmin(admin.ModelAdmin):
    list_display = ("automation_run", "organization_id", "step_type", "name", "status")
    list_filter = ("step_type", "status")
    search_fields = ("name", "error_message")
    readonly_fields = (
        "id",
        "organization_id",
        "input_payload",
        "output_payload",
        "error_code",
        "error_message",
        "created_at",
        "updated_at",
    )
