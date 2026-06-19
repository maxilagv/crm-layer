from rest_framework import serializers

from crm.contacts.models import Contact
from crm.conversations.models import Conversation
from crm.leads.domain.enums import (
    AuthoritySignal,
    BudgetSignal,
    LeadSourceType,
    LeadStage,
    LeadStatus,
    LeadTemperature,
    LeadUrgency,
)
from crm.leads.models import Lead, LeadScoreSnapshot, LeadSource, LeadStageHistory


class LeadContactSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    display_name = serializers.CharField()
    type = serializers.CharField()
    status = serializers.CharField()
    company_name = serializers.CharField()


class LeadScoreSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadScoreSnapshot
        fields = [
            "id",
            "score",
            "temperature",
            "reasoning_summary",
            "factors",
            "ai_run_id",
            "created_at",
        ]
        read_only_fields = fields


class LeadStageHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadStageHistory
        fields = [
            "id",
            "from_stage",
            "to_stage",
            "reason",
            "changed_by_id",
            "changed_by_type",
            "ai_run_id",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class LeadSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSource
        fields = [
            "id",
            "source_type",
            "source_detail",
            "campaign",
            "channel",
            "first_touch_message_id",
            "first_touch_conversation_id",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class LeadListSerializer(serializers.ModelSerializer):
    contact = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            "id",
            "contact",
            "status",
            "stage",
            "score",
            "temperature",
            "service_interest",
            "budget_signal",
            "urgency",
            "authority_signal",
            "next_best_action",
            "last_scored_at",
            "summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_contact(self, obj) -> dict:
        return {
            "id": str(obj.contact_id),
            "display_name": obj.contact.display_name,
            "type": obj.contact.type,
            "status": obj.contact.status,
            "company_name": obj.contact.company_name,
        }


class LeadDetailSerializer(LeadListSerializer):
    score_snapshots = LeadScoreSnapshotSerializer(many=True, read_only=True)
    stage_history = LeadStageHistorySerializer(many=True, read_only=True)
    sources = LeadSourceSerializer(many=True, read_only=True)

    class Meta(LeadListSerializer.Meta):
        fields = [
            *LeadListSerializer.Meta.fields,
            "pain_points",
            "technical_needs",
            "business_needs",
            "metadata",
            "score_snapshots",
            "stage_history",
            "sources",
        ]
        read_only_fields = fields


class LeadCreateSerializer(serializers.Serializer):
    contact_id = serializers.UUIDField()
    source_type = serializers.ChoiceField(
        choices=LeadSourceType.choices, default=LeadSourceType.MANUAL
    )
    metadata = serializers.DictField(required=False, default=dict)

    def validate_contact_id(self, value):
        organization = self.context["organization"]
        contact = Contact.objects.filter(id=value, organization_id=organization.id).first()
        if contact is None:
            raise serializers.ValidationError("Contact not found")
        self.context["contact"] = contact
        return value


class LeadUpdateSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=LeadStage.choices, required=False)
    status = serializers.ChoiceField(choices=LeadStatus.choices, required=False)
    temperature = serializers.ChoiceField(choices=LeadTemperature.choices, required=False)
    service_interest = serializers.CharField(max_length=255, required=False, allow_blank=True)
    budget_signal = serializers.ChoiceField(choices=BudgetSignal.choices, required=False)
    urgency = serializers.ChoiceField(choices=LeadUrgency.choices, required=False)
    authority_signal = serializers.ChoiceField(choices=AuthoritySignal.choices, required=False)
    pain_points = serializers.ListField(child=serializers.CharField(), required=False)
    technical_needs = serializers.ListField(child=serializers.CharField(), required=False)
    business_needs = serializers.ListField(child=serializers.CharField(), required=False)
    next_best_action = serializers.CharField(max_length=255, required=False, allow_blank=True)
    summary = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.DictField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class LeadScoreRequestSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField(required=False)
    use_ai = serializers.BooleanField(required=False, default=True)

    def validate_conversation_id(self, value):
        organization = self.context["organization"]
        conversation = Conversation.objects.filter(
            id=value, organization_id=organization.id
        ).first()
        if conversation is None:
            raise serializers.ValidationError("Conversation not found")
        self.context["conversation"] = conversation
        return value


class LeadMarkLostSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)


class LeadConvertSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class LeadFollowupSerializer(serializers.Serializer):
    due_at = serializers.DateTimeField(required=False)
    title = serializers.CharField(max_length=255, required=False, default="Seguimiento comercial")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    idempotency_key = serializers.CharField(required=False, allow_blank=True, default="")
