from rest_framework import serializers

from crm.contacts.models import Contact
from crm.conversations.models import Conversation
from crm.whatsapp.models import (
    WhatsAppOutboundMessage,
    WhatsAppTemplate,
    WhatsAppWebhookEvent,
)


class WhatsAppTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppTemplate
        fields = [
            "id",
            "name",
            "language",
            "category",
            "status",
            "components",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TemplateSendSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    contact_id = serializers.UUIDField()
    template_name = serializers.CharField(max_length=255)
    language = serializers.CharField(max_length=32)
    components = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    idempotency_key = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        organization = self.context["organization"]
        conversation = Conversation.objects.filter(
            id=attrs["conversation_id"],
            organization_id=organization.id,
        ).first()
        contact = Contact.objects.filter(
            id=attrs["contact_id"],
            organization_id=organization.id,
        ).first()
        if conversation is None:
            raise serializers.ValidationError({"conversation_id": "Conversation not found"})
        if contact is None:
            raise serializers.ValidationError({"contact_id": "Contact not found"})
        attrs["conversation"] = conversation
        attrs["contact"] = contact
        return attrs


class WhatsAppOutboundMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppOutboundMessage
        fields = [
            "id",
            "conversation_id",
            "contact_id",
            "message_type",
            "body",
            "template_name",
            "external_message_id",
            "status",
            "sent_at",
            "delivered_at",
            "read_at",
            "failed_at",
            "error_code",
            "error_message",
            "idempotency_key",
            "recipient_phone_e164",
            "queued_at",
            "last_attempt_at",
            "attempts",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class WhatsAppWebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppWebhookEvent
        fields = [
            "id",
            "event_id",
            "event_type",
            "status",
            "received_at",
            "processed_at",
            "error_message",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class WhatsAppWebhookEventRawSerializer(WhatsAppWebhookEventSerializer):
    class Meta(WhatsAppWebhookEventSerializer.Meta):
        fields = [*WhatsAppWebhookEventSerializer.Meta.fields, "raw_payload"]
