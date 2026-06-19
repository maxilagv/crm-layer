from django.contrib import admin

from .models import Task, TaskCommand, TaskComment, TaskReminder, TaskSource, TaskStatusHistory


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "organization_id", "status", "priority", "assigned_to", "due_at")
    list_filter = ("status", "priority", "source_type")
    search_fields = ("title", "description")
    readonly_fields = ("id", "organization_id", "created_at", "updated_at", "completed_at")
    date_hierarchy = "created_at"


@admin.register(TaskReminder)
class TaskReminderAdmin(admin.ModelAdmin):
    list_display = ("task", "organization_id", "channel", "status", "remind_at", "sent_at")
    list_filter = ("channel", "status")
    search_fields = ("task__title",)
    readonly_fields = ("id", "organization_id", "created_at", "updated_at", "sent_at")
    date_hierarchy = "remind_at"


@admin.register(TaskCommand)
class TaskCommandAdmin(admin.ModelAdmin):
    list_display = ("command_type", "organization_id", "task", "status", "created_at")
    list_filter = ("command_type", "status")
    search_fields = ("raw_command",)
    readonly_fields = (
        "id",
        "organization_id",
        "parsed_command",
        "result",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ("task", "organization_id", "author_type", "created_at")
    list_filter = ("author_type",)
    search_fields = ("body", "task__title")
    readonly_fields = ("id", "organization_id", "created_at", "updated_at")


@admin.register(TaskStatusHistory)
class TaskStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("task", "organization_id", "from_status", "to_status", "created_at")
    list_filter = ("to_status", "changed_by_type")
    search_fields = ("task__title", "reason")
    readonly_fields = ("id", "organization_id", "created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(TaskSource)
class TaskSourceAdmin(admin.ModelAdmin):
    list_display = ("task", "organization_id", "source_type", "source_id", "created_at")
    list_filter = ("source_type",)
    search_fields = ("task__title", "normalized_title")
    readonly_fields = ("id", "organization_id", "created_at", "updated_at", "normalized_title")
