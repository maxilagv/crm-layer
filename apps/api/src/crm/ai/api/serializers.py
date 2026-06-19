"""Serializers for AI admin endpoints.

``raw_response`` is intentionally NEVER exposed: it is a sanitized debugging
payload reachable only via Django admin.
"""

from rest_framework import serializers

from crm.ai.domain.enums import AIPurpose
from crm.ai.models import (
    AIEvalResult,
    AIMessage,
    AIModelConfig,
    AIPrompt,
    AIPromptVersion,
    AIProvider,
    AIRun,
    AIToolCall,
)


class AIRunListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIRun
        fields = [
            "id",
            "purpose",
            "status",
            "provider",
            "model",
            "usage_input_tokens",
            "usage_output_tokens",
            "estimated_cost",
            "latency_ms",
            "error_code",
            "conversation_id",
            "contact_id",
            "request_id",
            "created_at",
            "finished_at",
        ]
        read_only_fields = fields


class AIRunDetailSerializer(serializers.ModelSerializer):
    prompt_key = serializers.CharField(source="prompt_version.prompt.key", default=None)
    prompt_version_number = serializers.IntegerField(source="prompt_version.version", default=None)

    class Meta:
        model = AIRun
        fields = [
            "id",
            "purpose",
            "status",
            "provider",
            "model",
            "input_context",
            "output_text",
            "output_json",
            "tool_calls",
            "usage_input_tokens",
            "usage_output_tokens",
            "usage_total_tokens",
            "estimated_cost",
            "latency_ms",
            "error_code",
            "error_message",
            "safety_result",
            "prompt_key",
            "prompt_version_number",
            "conversation_id",
            "message_id",
            "contact_id",
            "lead_id",
            "client_id",
            "ticket_id",
            "task_id",
            "request_id",
            "correlation_id",
            "created_at",
            "started_at",
            "finished_at",
        ]
        read_only_fields = fields


class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = ["id", "role", "content", "content_type", "token_count", "created_at"]
        read_only_fields = fields


class AIToolCallSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIToolCall
        fields = [
            "id",
            "ai_run_id",
            "tool_name",
            "tool_version",
            "arguments",
            "validated_arguments",
            "result",
            "status",
            "error_code",
            "error_message",
            "started_at",
            "finished_at",
            "created_at",
        ]
        read_only_fields = fields


class AIPromptVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIPromptVersion
        fields = [
            "id",
            "version",
            "status",
            "system_prompt",
            "developer_prompt",
            "template",
            "output_schema",
            "examples",
            "change_notes",
            "activated_at",
            "archived_at",
            "created_at",
        ]
        read_only_fields = ["id", "version", "status", "activated_at", "archived_at", "created_at"]


class AIPromptSerializer(serializers.ModelSerializer):
    active_version = AIPromptVersionSerializer(read_only=True)

    class Meta:
        model = AIPrompt
        fields = ["id", "key", "name", "description", "purpose", "active_version", "created_at"]
        read_only_fields = ["id", "active_version", "created_at"]


class AIPromptCreateSerializer(serializers.Serializer):
    key = serializers.SlugField(max_length=120)
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    purpose = serializers.ChoiceField(choices=AIPurpose.choices)


class AIPromptUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)


class AIPromptVersionCreateSerializer(serializers.Serializer):
    system_prompt = serializers.CharField()
    developer_prompt = serializers.CharField(required=False, allow_blank=True, default="")
    template = serializers.CharField(required=False, allow_blank=True, default="")
    output_schema = serializers.JSONField(required=False, allow_null=True, default=None)
    examples = serializers.JSONField(required=False, default=list)
    change_notes = serializers.CharField(required=False, allow_blank=True, default="")


class AIModelConfigSerializer(serializers.ModelSerializer):
    provider_type = serializers.CharField(source="provider.provider_type", read_only=True)

    class Meta:
        model = AIModelConfig
        fields = [
            "id",
            "provider",
            "provider_type",
            "purpose",
            "model_name",
            "temperature",
            "max_tokens",
            "timeout_seconds",
            "fallback_model",
            "fallback_provider",
            "is_active",
            "supports_tools",
            "supports_structured_outputs",
            "supports_audio",
            "supports_images",
            "supports_embeddings",
            "created_at",
        ]
        read_only_fields = ["id", "provider_type", "created_at"]

    def validate_provider(self, provider: AIProvider) -> AIProvider:
        organization = self.context.get("organization")
        if organization is not None and provider.organization_id != organization.id:
            raise serializers.ValidationError("Provider belongs to another organization")
        return provider


class ToolDefinitionSerializer(serializers.Serializer):
    name = serializers.CharField()
    version = serializers.CharField()
    description = serializers.CharField()
    argument_schema = serializers.JSONField()
    permissions_required = serializers.ListField(child=serializers.CharField())
    allowed_purposes = serializers.ListField(child=serializers.CharField())
    side_effects = serializers.CharField()
    risk_level = serializers.CharField()
    requires_human_approval = serializers.BooleanField()


class AIEvalResultSerializer(serializers.ModelSerializer):
    suite_name = serializers.CharField(source="eval_case.suite_name", read_only=True)
    case_key = serializers.CharField(source="eval_case.case_key", read_only=True)

    class Meta:
        model = AIEvalResult
        fields = [
            "id",
            "suite_name",
            "case_key",
            "provider",
            "model",
            "actual_output",
            "passed",
            "score",
            "metrics",
            "error_message",
            "created_at",
        ]
        read_only_fields = fields


class EvalRunRequestSerializer(serializers.Serializer):
    suite_name = serializers.CharField(required=False, allow_blank=True, default="")
