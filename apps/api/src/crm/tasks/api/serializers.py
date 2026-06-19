from rest_framework import serializers

from crm.accounts.models import User
from crm.tasks.domain.enums import (
    TaskPriority,
    TaskReminderChannel,
    TaskStatus,
)
from crm.tasks.models import Task, TaskComment, TaskReminder, TaskSource, TaskStatusHistory


class TaskReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskReminder
        fields = [
            "id",
            "remind_at",
            "channel",
            "status",
            "sent_at",
            "acknowledged_at",
            "snoozed_until",
            "notification_id",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class TaskStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStatusHistory
        fields = [
            "id",
            "from_status",
            "to_status",
            "reason",
            "changed_by_id",
            "changed_by_type",
            "created_at",
        ]
        read_only_fields = fields


class TaskSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskSource
        fields = [
            "id",
            "source_type",
            "source_id",
            "source_message_id",
            "ai_run_id",
            "normalized_title",
            "created_at",
        ]
        read_only_fields = fields


class TaskCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskComment
        fields = ["id", "author_type", "author_id", "body", "metadata", "created_at"]
        read_only_fields = fields


class TaskListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "source_type",
            "source_id",
            "contact_id",
            "lead_id",
            "client_id",
            "ticket_id",
            "conversation_id",
            "assigned_to_id",
            "due_at",
            "completed_at",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TaskDetailSerializer(TaskListSerializer):
    reminders = TaskReminderSerializer(many=True, read_only=True)
    comments = TaskCommentSerializer(many=True, read_only=True)
    status_history = TaskStatusHistorySerializer(many=True, read_only=True)
    sources = TaskSourceSerializer(many=True, read_only=True)

    class Meta(TaskListSerializer.Meta):
        fields = [
            *TaskListSerializer.Meta.fields,
            "reminders",
            "comments",
            "status_history",
            "sources",
        ]
        read_only_fields = fields


class TaskCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    priority = serializers.ChoiceField(choices=TaskPriority.choices, default=TaskPriority.MEDIUM)
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    contact_id = serializers.UUIDField(required=False, allow_null=True)
    lead_id = serializers.UUIDField(required=False, allow_null=True)
    client_id = serializers.UUIDField(required=False, allow_null=True)
    ticket_id = serializers.UUIDField(required=False, allow_null=True)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    assigned_to_id = serializers.UUIDField(required=False, allow_null=True)
    metadata = serializers.DictField(required=False, default=dict)
    idempotency_key = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_assigned_to_id(self, value):
        if value is None:
            return value
        organization = self.context["organization"]
        user = User.objects.filter(id=value, memberships__organization=organization).first()
        if user is None:
            raise serializers.ValidationError("Assigned user not found in organization")
        self.context["assigned_to"] = user
        return value


class TaskUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=TaskStatus.choices, required=False)
    priority = serializers.ChoiceField(choices=TaskPriority.choices, required=False)
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    assigned_to_id = serializers.UUIDField(required=False, allow_null=True)
    contact_id = serializers.UUIDField(required=False, allow_null=True)
    lead_id = serializers.UUIDField(required=False, allow_null=True)
    client_id = serializers.UUIDField(required=False, allow_null=True)
    ticket_id = serializers.UUIDField(required=False, allow_null=True)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    metadata = serializers.DictField(required=False)

    def validate_assigned_to_id(self, value):
        if value is None:
            self.context["assigned_to"] = None
            return value
        organization = self.context["organization"]
        user = User.objects.filter(id=value, memberships__organization=organization).first()
        if user is None:
            raise serializers.ValidationError("Assigned user not found in organization")
        self.context["assigned_to"] = user
        return value


class TaskSnoozeSerializer(serializers.Serializer):
    snooze_until = serializers.DateTimeField()


class TaskReminderCreateSerializer(serializers.Serializer):
    remind_at = serializers.DateTimeField()
    channel = serializers.ChoiceField(
        choices=TaskReminderChannel.choices, default=TaskReminderChannel.WHATSAPP
    )
    metadata = serializers.DictField(required=False, default=dict)
