from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers

from crm.business_settings.models import (
    AIBehaviorPolicy,
    BusinessProfile,
    NotificationPolicy,
    ProspectingPolicy,
    SalesPolicy,
    SupportPolicy,
    WhatsAppPolicy,
)


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise serializers.ValidationError("Invalid timezone") from exc
    return value


class JSONListField(serializers.ListField):
    def __init__(self, **kwargs):
        super().__init__(child=serializers.CharField(max_length=500), **kwargs)


class BusinessProfileSerializer(serializers.ModelSerializer):
    services_offered = JSONListField(required=False)
    target_clients = JSONListField(required=False)
    signature_phrases = JSONListField(required=False)

    class Meta:
        model = BusinessProfile
        fields = [
            "id",
            "business_name",
            "owner_name",
            "owner_phone",
            "default_language",
            "timezone",
            "business_description",
            "services_offered",
            "target_clients",
            "brand_tone",
            "calendar_link",
            "website_url",
            "owner_writing_style",
            "signature_phrases",
            "closer_name",
            "closer_whatsapp",
            "closer_role",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_timezone(self, value):
        return validate_timezone(value)


class SalesPolicySerializer(serializers.ModelSerializer):
    common_objections = JSONListField(required=False)
    forbidden_claims = JSONListField(required=False)

    class Meta:
        model = SalesPolicy
        fields = [
            "id",
            "main_sales_goal",
            "call_to_action",
            "can_quote_prices",
            "price_min",
            "price_max",
            "price_policy_text",
            "must_handoff_for_price",
            "common_objections",
            "forbidden_claims",
            "sales_tone",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        price_min = attrs.get("price_min", getattr(self.instance, "price_min", None))
        price_max = attrs.get("price_max", getattr(self.instance, "price_max", None))
        if price_min is not None and price_max is not None:
            if Decimal(price_min) > Decimal(price_max):
                raise serializers.ValidationError(
                    {"price_min": "Must be less than or equal to price_max"}
                )
        return attrs


class SupportPolicySerializer(serializers.ModelSerializer):
    allowed_support_actions = JSONListField(required=False)
    forbidden_support_actions = JSONListField(required=False)
    urgent_keywords = JSONListField(required=False)
    critical_ticket_rules = JSONListField(required=False)

    class Meta:
        model = SupportPolicy
        fields = [
            "id",
            "support_hours",
            "allowed_support_actions",
            "forbidden_support_actions",
            "urgent_keywords",
            "critical_ticket_rules",
            "data_request_policy",
            "default_support_reply",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AIBehaviorPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AIBehaviorPolicy
        fields = [
            "id",
            "default_provider",
            "fallback_provider",
            "default_sales_model",
            "default_support_model",
            "max_context_messages",
            "temperature_sales",
            "temperature_support",
            "auto_reply_enabled",
            "human_handoff_required_for_risks",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class NotificationPolicySerializer(serializers.ModelSerializer):
    notification_channels = JSONListField(required=False)

    class Meta:
        model = NotificationPolicy
        fields = [
            "id",
            "notify_on_new_lead",
            "notify_on_human_handoff",
            "notify_on_failed_ai_reply",
            "notification_channels",
            "quiet_hours",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class WhatsAppPolicySerializer(serializers.ModelSerializer):
    handoff_keywords = JSONListField(required=False)
    opt_out_keywords = JSONListField(required=False)
    allowed_outbound_templates = JSONListField(required=False)

    class Meta:
        model = WhatsAppPolicy
        fields = [
            "id",
            "auto_reply_enabled",
            "business_hours",
            "handoff_keywords",
            "opt_out_keywords",
            "allowed_outbound_templates",
            "media_download_enabled",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProspectingPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProspectingPolicy
        fields = [
            "id",
            "agent_paused",
            "send_start_hour",
            "send_cutoff_hour",
            "org_daily_cap",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        start = attrs.get("send_start_hour", getattr(self.instance, "send_start_hour", 9))
        cutoff = attrs.get("send_cutoff_hour", getattr(self.instance, "send_cutoff_hour", 18))
        if start >= cutoff:
            raise serializers.ValidationError(
                {"send_cutoff_hour": "Must be greater than send_start_hour"}
            )
        return attrs
