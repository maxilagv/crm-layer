from rest_framework import serializers

from crm.support.domain.enums import (
    AttachmentType,
    CommentVisibility,
    KnownIssueSeverity,
    KnownIssueStatus,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)
from crm.support.models import (
    SupportKnownIssue,
    SupportTicket,
    SupportTicketAttachment,
    SupportTicketComment,
)


class SupportTicketCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicketComment
        fields = ["id", "author_type", "author_id", "body", "visibility", "created_at"]
        read_only_fields = fields


class SupportTicketAttachmentSerializer(serializers.ModelSerializer):
    mime_type = serializers.CharField(source="media_asset.mime_type", read_only=True)
    file_name = serializers.CharField(source="media_asset.file_name", read_only=True)

    class Meta:
        model = SupportTicketAttachment
        fields = [
            "id",
            "media_asset_id",
            "attachment_type",
            "mime_type",
            "file_name",
            "source_message_id",
            "created_at",
        ]
        read_only_fields = fields


class SupportTicketListSerializer(serializers.ModelSerializer):
    contact_display_name = serializers.CharField(source="contact.display_name", read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "title",
            "status",
            "priority",
            "category",
            "client_id",
            "contact_id",
            "contact_display_name",
            "assigned_user_id",
            "conversation_id",
            "due_at",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SupportTicketDetailSerializer(serializers.ModelSerializer):
    comments = SupportTicketCommentSerializer(many=True, read_only=True)
    attachments = SupportTicketAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "client_id",
            "contact_id",
            "conversation_id",
            "source_message_id",
            "status",
            "priority",
            "category",
            "title",
            "description",
            "technical_summary",
            "ai_summary",
            "assigned_user_id",
            "due_at",
            "resolved_at",
            "metadata",
            "comments",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SupportTicketCreateSerializer(serializers.Serializer):
    contact_id = serializers.UUIDField()
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    category = serializers.ChoiceField(choices=TicketCategory.choices, required=False)
    priority = serializers.ChoiceField(choices=TicketPriority.choices, required=False)
    conversation_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class SupportTicketUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=TicketStatus.choices, required=False)
    priority = serializers.ChoiceField(choices=TicketPriority.choices, required=False)
    category = serializers.ChoiceField(choices=TicketCategory.choices, required=False)
    due_at = serializers.DateTimeField(required=False, allow_null=True)


class TicketAssignSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()


class TicketResolveSerializer(serializers.Serializer):
    summary = serializers.CharField(max_length=5000)
    root_cause = serializers.CharField(required=False, allow_blank=True, default="")
    resolution_steps = serializers.CharField(required=False, allow_blank=True, default="")


class TicketReopenSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class TicketCommentCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=10000)
    visibility = serializers.ChoiceField(
        choices=CommentVisibility.choices, default=CommentVisibility.INTERNAL
    )


class TicketAttachmentCreateSerializer(serializers.Serializer):
    media_asset_id = serializers.UUIDField()
    attachment_type = serializers.ChoiceField(
        choices=AttachmentType.choices, default=AttachmentType.OTHER
    )
    source_message_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class KnownIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportKnownIssue
        fields = [
            "id",
            "title",
            "description",
            "category",
            "status",
            "severity",
            "matching_keywords",
            "resolution_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class KnownIssueCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    category = serializers.ChoiceField(
        choices=TicketCategory.choices, default=TicketCategory.UNKNOWN
    )
    severity = serializers.ChoiceField(
        choices=KnownIssueSeverity.choices, default=KnownIssueSeverity.MEDIUM
    )
    matching_keywords = serializers.ListField(
        child=serializers.CharField(max_length=80), required=False, default=list
    )
    resolution_notes = serializers.CharField(required=False, allow_blank=True, default="")


class KnownIssueUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=KnownIssueStatus.choices, required=False)
    severity = serializers.ChoiceField(choices=KnownIssueSeverity.choices, required=False)
    matching_keywords = serializers.ListField(child=serializers.CharField(), required=False)
    resolution_notes = serializers.CharField(required=False, allow_blank=True)
