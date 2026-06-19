from django.contrib import admin

from .models import (
    SalesCallRequest,
    SalesFollowup,
    SalesObjection,
    SalesOpportunity,
    SalesPlaybook,
)


@admin.register(SalesOpportunity)
class SalesOpportunityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization_id",
        "lead",
        "title",
        "stage",
        "probability",
        "expected_close_date",
    )
    list_filter = ("stage", "currency")
    search_fields = ("title", "lead__contact__display_name")
    readonly_fields = ("id", "created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(SalesFollowup)
class SalesFollowupAdmin(admin.ModelAdmin):
    list_display = ("id", "organization_id", "lead", "title", "status", "due_at")
    list_filter = ("status",)
    search_fields = ("title", "notes", "lead__contact__display_name")
    readonly_fields = ("id", "idempotency_key", "created_at", "updated_at")
    date_hierarchy = "due_at"


@admin.register(SalesObjection)
class SalesObjectionAdmin(admin.ModelAdmin):
    list_display = ("id", "organization_id", "lead", "objection_type", "resolved", "created_at")
    list_filter = ("objection_type", "resolved")
    search_fields = ("summary", "raw_text", "lead__contact__display_name")
    readonly_fields = ("id", "message", "raw_text", "created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(SalesPlaybook)
class SalesPlaybookAdmin(admin.ModelAdmin):
    list_display = ("id", "organization_id", "key", "name", "status")
    list_filter = ("status",)
    search_fields = ("key", "name", "description")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(SalesCallRequest)
class SalesCallRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization_id",
        "lead",
        "contact",
        "status",
        "requested_at",
        "scheduled_at",
    )
    list_filter = ("status",)
    search_fields = ("lead__contact__display_name", "contact__display_name", "notes")
    readonly_fields = ("id", "owner_notified_at", "created_at", "updated_at")
    date_hierarchy = "requested_at"
