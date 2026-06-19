from django.contrib import admin

from .models import Prospect, ProspectingCampaign


@admin.register(ProspectingCampaign)
class ProspectingCampaignAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "vertical",
        "status",
        "channel",
        "source",
        "auto_reply",
        "auto_followup",
        "discovered_count",
        "created_at",
    )
    list_filter = ("status", "channel", "source", "auto_reply", "auto_followup")
    search_fields = ("name", "vertical", "query")
    readonly_fields = ("created_at", "updated_at", "last_run_at")


@admin.register(Prospect)
class ProspectAdmin(admin.ModelAdmin):
    list_display = (
        "business_name",
        "campaign",
        "status",
        "fit_score",
        "owner_email",
        "touch_count",
        "phone",
        "created_at",
    )
    list_filter = ("status", "external_source")
    search_fields = ("business_name", "place_id", "external_id", "owner_email", "phone")
    readonly_fields = ("created_at", "updated_at", "place_id", "external_id", "raw_data")
