from django.contrib import admin

from .models import (
    SupportKnownIssue,
    SupportResolution,
    SupportTicket,
    SupportTicketAttachment,
    SupportTicketComment,
    SupportTicketEvent,
)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "priority",
        "category",
        "client",
        "assigned_user",
        "created_at",
    )
    list_filter = ("status", "priority", "category")
    search_fields = ("title", "description", "id")
    date_hierarchy = "created_at"
    readonly_fields = (
        "id",
        "source_message_id",
        "conversation_id",
        "resolved_at",
        "created_at",
        "updated_at",
    )


@admin.register(SupportTicketEvent)
class SupportTicketEventAdmin(admin.ModelAdmin):
    list_display = ("ticket", "event_type", "actor_type", "from_status", "to_status", "created_at")
    list_filter = ("event_type", "actor_type")
    date_hierarchy = "created_at"
    readonly_fields = tuple(f.name for f in SupportTicketEvent._meta.fields)

    def has_add_permission(self, request):
        return False


@admin.register(SupportTicketComment)
class SupportTicketCommentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author_type", "visibility", "created_at")
    list_filter = ("visibility", "author_type")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(SupportTicketAttachment)
class SupportTicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "attachment_type", "media_asset", "created_at")
    list_filter = ("attachment_type",)
    readonly_fields = tuple(f.name for f in SupportTicketAttachment._meta.fields)

    def has_add_permission(self, request):
        return False


@admin.register(SupportKnownIssue)
class SupportKnownIssueAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "severity", "created_at")
    list_filter = ("status", "severity", "category")
    search_fields = ("title", "description")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(SupportResolution)
class SupportResolutionAdmin(admin.ModelAdmin):
    list_display = ("ticket", "resolved_by_type", "created_at")
    list_filter = ("resolved_by_type",)
    readonly_fields = tuple(f.name for f in SupportResolution._meta.fields)

    def has_add_permission(self, request):
        return False
