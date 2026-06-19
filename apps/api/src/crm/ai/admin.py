from django.contrib import admin

from .models import (
    AIEvalCase,
    AIEvalResult,
    AIModelConfig,
    AIPrompt,
    AIPromptVersion,
    AIProvider,
    AIRun,
    AIToolCall,
    AIUsageRecord,
)


@admin.register(AIProvider)
class AIProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "provider_type", "organization_id", "is_enabled", "priority")
    list_filter = ("provider_type", "is_enabled")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AIModelConfig)
class AIModelConfigAdmin(admin.ModelAdmin):
    list_display = ("purpose", "model_name", "provider", "organization_id", "is_active")
    list_filter = ("purpose", "is_active")
    search_fields = ("model_name",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AIPrompt)
class AIPromptAdmin(admin.ModelAdmin):
    list_display = ("key", "purpose", "organization_id", "active_version")
    list_filter = ("purpose",)
    search_fields = ("key", "name")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AIPromptVersion)
class AIPromptVersionAdmin(admin.ModelAdmin):
    list_display = ("prompt", "version", "status", "activated_at", "archived_at")
    list_filter = ("status",)
    search_fields = ("prompt__key",)
    readonly_fields = ("id", "created_at", "updated_at", "activated_at", "archived_at")


@admin.register(AIRun)
class AIRunAdmin(admin.ModelAdmin):
    list_display = (
        "purpose",
        "status",
        "provider",
        "model",
        "estimated_cost",
        "latency_ms",
        "created_at",
    )
    list_filter = ("purpose", "status", "provider")
    search_fields = ("id", "request_id", "correlation_id")
    # Inputs/outputs are sanitized at write time but stay read-only in admin.
    readonly_fields = tuple(field.name for field in AIRun._meta.fields)

    def has_add_permission(self, request):
        return False


@admin.register(AIToolCall)
class AIToolCallAdmin(admin.ModelAdmin):
    list_display = ("tool_name", "status", "ai_run", "error_code", "created_at")
    list_filter = ("tool_name", "status")
    search_fields = ("tool_name", "ai_run__id")
    readonly_fields = tuple(field.name for field in AIToolCall._meta.fields)

    def has_add_permission(self, request):
        return False


@admin.register(AIUsageRecord)
class AIUsageRecordAdmin(admin.ModelAdmin):
    list_display = ("purpose", "provider", "model", "estimated_cost", "created_at")
    list_filter = ("purpose", "provider")
    readonly_fields = tuple(field.name for field in AIUsageRecord._meta.fields)

    def has_add_permission(self, request):
        return False


@admin.register(AIEvalCase)
class AIEvalCaseAdmin(admin.ModelAdmin):
    list_display = ("suite_name", "case_key", "purpose", "is_active")
    list_filter = ("suite_name", "purpose", "is_active")
    search_fields = ("case_key",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AIEvalResult)
class AIEvalResultAdmin(admin.ModelAdmin):
    list_display = ("eval_case", "passed", "score", "created_at")
    list_filter = ("passed",)
    readonly_fields = tuple(field.name for field in AIEvalResult._meta.fields)

    def has_add_permission(self, request):
        return False
