from rest_framework import serializers

from crm.automations.domain.enums import (
    AutomationActionType,
    AutomationRunStatus,
    AutomationTriggerType,
)
from crm.automations.models import (
    AutomationAction,
    AutomationCondition,
    AutomationRule,
    AutomationRun,
    AutomationRunStep,
    AutomationTrigger,
)


class AutomationTriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationTrigger
        fields = ["id", "trigger_type", "configuration", "created_at"]
        read_only_fields = fields


class AutomationConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationCondition
        fields = [
            "id",
            "order",
            "condition_type",
            "field_path",
            "operator",
            "expected_value",
            "configuration",
        ]
        read_only_fields = fields


class AutomationActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationAction
        fields = [
            "id",
            "order",
            "action_type",
            "configuration",
            "required_permission",
            "timeout_seconds",
        ]
        read_only_fields = fields


class AutomationRuleSerializer(serializers.ModelSerializer):
    triggers = AutomationTriggerSerializer(many=True, read_only=True)
    condition_rows = AutomationConditionSerializer(many=True, read_only=True)
    action_rows = AutomationActionSerializer(many=True, read_only=True)

    class Meta:
        model = AutomationRule
        fields = [
            "id",
            "name",
            "description",
            "trigger_type",
            "conditions",
            "actions",
            "is_enabled",
            "priority",
            "created_by_id",
            "metadata",
            "created_at",
            "updated_at",
            "triggers",
            "condition_rows",
            "action_rows",
        ]
        read_only_fields = [
            "id",
            "created_by_id",
            "created_at",
            "updated_at",
            "triggers",
            "condition_rows",
            "action_rows",
        ]


class AutomationRuleCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    trigger_type = serializers.ChoiceField(choices=AutomationTriggerType.choices)
    conditions = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    actions = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    is_enabled = serializers.BooleanField(required=False, default=True)
    priority = serializers.IntegerField(required=False, min_value=0, max_value=1000, default=100)
    metadata = serializers.DictField(required=False, default=dict)

    def validate_actions(self, value):
        for action in value:
            action_type = action.get("type") or action.get("action_type")
            if action_type not in AutomationActionType.values:
                raise serializers.ValidationError(f"Unsupported action: {action_type}")
        return value


class AutomationRuleUpdateSerializer(AutomationRuleCreateSerializer):
    name = serializers.CharField(max_length=255, required=False)
    trigger_type = serializers.ChoiceField(choices=AutomationTriggerType.choices, required=False)


class AutomationRunStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationRunStep
        fields = [
            "id",
            "step_type",
            "name",
            "status",
            "input_payload",
            "output_payload",
            "error_code",
            "error_message",
            "started_at",
            "finished_at",
        ]
        read_only_fields = fields


class AutomationRunSerializer(serializers.ModelSerializer):
    steps = AutomationRunStepSerializer(many=True, read_only=True)

    class Meta:
        model = AutomationRun
        fields = [
            "id",
            "rule_id",
            "trigger_type",
            "trigger_event_id",
            "status",
            "trigger_payload",
            "reason",
            "started_at",
            "finished_at",
            "created_at",
            "steps",
        ]
        read_only_fields = fields


class AutomationDispatchSerializer(serializers.Serializer):
    trigger_type = serializers.ChoiceField(choices=AutomationTriggerType.choices)
    payload = serializers.DictField(default=dict)
    trigger_event_id = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_trigger_event_id(self, value):
        return value[:255]

    def validate_status(self, value):
        if value not in AutomationRunStatus.values:
            raise serializers.ValidationError("Invalid run status")
        return value
