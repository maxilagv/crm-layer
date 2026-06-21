from rest_framework import serializers

from crm.prospecting.domain.enums import (
    CampaignSource,
    CampaignStatus,
    ProspectChannel,
    ProspectStatus,
)
from crm.prospecting.models import Prospect, ProspectingCampaign


class ProspectingCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProspectingCampaign
        fields = [
            "id",
            "name",
            "vertical",
            "query",
            "location_hint",
            "status",
            "channel",
            "source",
            "target_profile",
            "min_fit_score",
            "auto_contact",
            "auto_reply",
            "auto_followup",
            "max_touches",
            "daily_cap",
            "discovered_count",
            "qualified_count",
            "contacted_count",
            "interested_count",
            "last_run_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "discovered_count",
            "qualified_count",
            "contacted_count",
            "interested_count",
            "last_run_at",
            "created_at",
            "updated_at",
        ]


class CampaignCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    query = serializers.CharField(max_length=255)
    vertical = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    location_hint = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    channel = serializers.ChoiceField(
        choices=ProspectChannel.choices, required=False, default=ProspectChannel.WHATSAPP.value
    )
    source = serializers.ChoiceField(
        choices=CampaignSource.choices,
        required=False,
        default=CampaignSource.GOOGLE_PLACES.value,
    )
    target_profile = serializers.CharField(required=False, allow_blank=True, default="")
    min_fit_score = serializers.IntegerField(min_value=0, max_value=100, required=False, default=60)
    auto_contact = serializers.BooleanField(required=False, default=False)
    auto_reply = serializers.BooleanField(required=False, default=False)
    auto_followup = serializers.BooleanField(required=False, default=False)
    max_touches = serializers.IntegerField(min_value=1, max_value=20, required=False, default=3)
    daily_cap = serializers.IntegerField(min_value=1, max_value=500, required=False, default=20)


class CampaignUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    vertical = serializers.CharField(max_length=120, required=False, allow_blank=True)
    query = serializers.CharField(max_length=255, required=False)
    location_hint = serializers.CharField(max_length=255, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=CampaignStatus.choices, required=False)
    channel = serializers.ChoiceField(choices=ProspectChannel.choices, required=False)
    source = serializers.ChoiceField(choices=CampaignSource.choices, required=False)
    target_profile = serializers.CharField(required=False, allow_blank=True)
    min_fit_score = serializers.IntegerField(min_value=0, max_value=100, required=False)
    auto_contact = serializers.BooleanField(required=False)
    auto_reply = serializers.BooleanField(required=False)
    auto_followup = serializers.BooleanField(required=False)
    max_touches = serializers.IntegerField(min_value=1, max_value=20, required=False)
    daily_cap = serializers.IntegerField(min_value=1, max_value=500, required=False)


class ProspectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prospect
        fields = [
            "id",
            "campaign",
            "place_id",
            "external_source",
            "external_id",
            "business_name",
            "category",
            "address",
            "phone",
            "website",
            "rating",
            "reviews_count",
            "photos_count",
            "status",
            "fit_score",
            "signals",
            "reasoning",
            "recommended_angle",
            "owner_name",
            "owner_email",
            "owner_email_score",
            "owner_title",
            "contact_id",
            "conversation_id",
            "lead_id",
            "qualified_at",
            "contacted_at",
            "replied_at",
            "touch_count",
            "last_touch_at",
            "next_followup_at",
            "follow_up_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ProspectUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ProspectStatus.choices)


class ProspectingReportContactSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    business_name = serializers.CharField()
    status = serializers.CharField()
    bucket = serializers.CharField()
    last_touch_at = serializers.DateTimeField(allow_null=True)
    fit_score = serializers.IntegerField(allow_null=True)
    owner_email = serializers.CharField(allow_blank=True)
    phone = serializers.CharField(allow_blank=True)


class ProspectingReportSerializer(serializers.Serializer):
    contacts = ProspectingReportContactSerializer(many=True)
    buckets = serializers.DictField(child=serializers.IntegerField())
    progress_pct = serializers.FloatField()
    totals = serializers.DictField()
