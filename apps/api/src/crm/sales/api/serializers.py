from rest_framework import serializers

from crm.leads.models import Lead
from crm.sales.domain.enums import CallRequestStatus, OpportunityStage
from crm.sales.models import SalesCallRequest, SalesOpportunity


class SalesOpportunitySerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source="contact.display_name", read_only=True)

    class Meta:
        model = SalesOpportunity
        fields = [
            "id",
            "lead_id",
            "contact_id",
            "contact_name",
            "title",
            "value_estimate_min",
            "value_estimate_max",
            "currency",
            "stage",
            "probability",
            "expected_close_date",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SalesOpportunityCreateSerializer(serializers.Serializer):
    lead_id = serializers.UUIDField()
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    value_estimate_min = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    value_estimate_max = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    currency = serializers.CharField(max_length=8, required=False, default="USD")
    stage = serializers.ChoiceField(
        choices=OpportunityStage.choices, required=False, default=OpportunityStage.NEW
    )
    probability = serializers.IntegerField(min_value=0, max_value=100, required=False)
    expected_close_date = serializers.DateField(required=False)
    metadata = serializers.DictField(required=False, default=dict)

    def validate_lead_id(self, value):
        organization = self.context["organization"]
        lead = (
            Lead.objects.filter(id=value, organization_id=organization.id)
            .select_related("contact")
            .first()
        )
        if lead is None:
            raise serializers.ValidationError("Lead not found")
        self.context["lead"] = lead
        return value

    def validate(self, attrs):
        min_value = attrs.get("value_estimate_min")
        max_value = attrs.get("value_estimate_max")
        if min_value is not None and max_value is not None and min_value > max_value:
            raise serializers.ValidationError("value_estimate_min must be <= value_estimate_max")
        return attrs


class SalesCallRequestSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source="contact.display_name", read_only=True)

    class Meta:
        model = SalesCallRequest
        fields = [
            "id",
            "lead_id",
            "contact_id",
            "contact_name",
            "conversation_id",
            "status",
            "requested_at",
            "scheduled_at",
            "owner_notified_at",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SalesCallRequestMarkScheduledSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(
        choices=CallRequestStatus.choices,
        required=False,
        default=CallRequestStatus.SCHEDULED,
    )
