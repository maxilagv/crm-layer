from django.contrib import admin

from .models import Lead, LeadScoreSnapshot, LeadSource, LeadStageHistory


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("id", "organization_id", "contact", "status", "stage", "score", "temperature")
    list_filter = ("status", "stage", "temperature", "budget_signal", "urgency")
    search_fields = ("contact__display_name", "service_interest", "summary")
    readonly_fields = ("id", "created_at", "updated_at", "last_scored_at")
    date_hierarchy = "created_at"


@admin.register(LeadScoreSnapshot)
class LeadScoreSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization_id",
        "lead",
        "score",
        "temperature",
        "ai_run_id",
        "created_at",
    )
    list_filter = ("temperature",)
    search_fields = ("lead__contact__display_name", "reasoning_summary")
    readonly_fields = ("id", "lead", "score", "temperature", "factors", "ai_run_id", "created_at")
    date_hierarchy = "created_at"


@admin.register(LeadStageHistory)
class LeadStageHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization_id",
        "lead",
        "from_stage",
        "to_stage",
        "changed_by_type",
        "created_at",
    )
    list_filter = ("to_stage", "changed_by_type")
    search_fields = ("lead__contact__display_name", "reason")
    readonly_fields = (
        "id",
        "lead",
        "from_stage",
        "to_stage",
        "changed_by_id",
        "ai_run_id",
        "created_at",
    )
    date_hierarchy = "created_at"


@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization_id",
        "lead",
        "source_type",
        "channel",
        "campaign",
        "created_at",
    )
    list_filter = ("source_type", "channel")
    search_fields = ("lead__contact__display_name", "source_detail", "campaign")
    readonly_fields = ("id", "created_at", "updated_at")
    date_hierarchy = "created_at"
