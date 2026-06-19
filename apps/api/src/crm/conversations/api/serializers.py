"""Serializers for the conversations API.

The inbox serializer reads last-message fields annotated by the selector (no
N+1). ``raw_payload`` and ``metadata`` of messages are never exposed.
"""

from rest_framework import serializers

from crm.conversations.constants import MessageType
from crm.conversations.models import Conversation, Message, MessageAttachment

BODY_PREVIEW_LENGTH = 140


def _assigned_user(conversation) -> dict | None:
    if conversation.assigned_user_id is None:
        return None
    return {
        "id": str(conversation.assigned_user_id),
        "name": getattr(conversation.assigned_user, "name", ""),
    }


def _contact_summary(conversation) -> dict:
    contact = conversation.contact
    phones = list(contact.phones.all())
    return {
        "id": str(contact.id),
        "display_name": contact.display_name,
        "type": contact.type,
        "status": contact.status,
        "primary_phone": phones[0].phone_e164 if phones else None,
    }


class ConversationInboxSerializer(serializers.ModelSerializer):
    assigned_user = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "channel",
            "status",
            "mode",
            "ai_enabled",
            "assigned_user",
            "contact",
            "last_message",
            "last_message_at",
            "last_inbound_at",
            "last_outbound_at",
            "summary",
        ]
        read_only_fields = fields

    def get_assigned_user(self, obj) -> dict | None:
        return _assigned_user(obj)

    def get_contact(self, obj) -> dict:
        return _contact_summary(obj)

    def get_last_message(self, obj) -> dict | None:
        last_id = getattr(obj, "last_message_id", None)
        if not last_id:
            return None
        body = getattr(obj, "last_message_body", "") or ""
        return {
            "id": str(last_id),
            "direction": getattr(obj, "last_message_direction", None),
            "message_type": getattr(obj, "last_message_type", None),
            "body_preview": body[:BODY_PREVIEW_LENGTH],
            "status": getattr(obj, "last_message_status", None),
            "created_at": getattr(obj, "last_message_created_at", None),
        }


class ConversationDetailSerializer(serializers.ModelSerializer):
    assigned_user = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "channel",
            "status",
            "mode",
            "ai_enabled",
            "assigned_user",
            "contact",
            "last_message_at",
            "last_inbound_at",
            "last_outbound_at",
            "summary",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_assigned_user(self, obj) -> dict | None:
        return _assigned_user(obj)

    def get_contact(self, obj) -> dict:
        return _contact_summary(obj)


class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttachment
        fields = [
            "id",
            "media_asset_id",
            "external_media_id",
            "mime_type",
            "file_name",
            "size_bytes",
        ]
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    attachments = MessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        # raw_payload and metadata are deliberately excluded from public output.
        fields = [
            "id",
            "direction",
            "message_type",
            "body",
            "normalized_text",
            "status",
            "external_message_id",
            "external_timestamp",
            "attachments",
            "created_at",
        ]
        read_only_fields = fields


class SendMessageSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=20000, required=False, allow_blank=True, default="")
    message_type = serializers.ChoiceField(choices=MessageType.choices, default=MessageType.TEXT)
    metadata = serializers.DictField(required=False, default=dict)

    def validate(self, attrs):
        if attrs["message_type"] == MessageType.TEXT and not attrs["body"].strip():
            raise serializers.ValidationError({"body": "Body is required for text messages"})
        return attrs


class ConversationActionSerializer(serializers.Serializer):
    assigned_user_id = serializers.UUIDField(required=False)
