from rest_framework import serializers

from crm.audit.models import (
    AuditAIDecision,
    AuditDataAccessLog,
    AuditExternalRequest,
    AuditLog,
    AuditSecurityEvent,
)


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor_type",
            "actor_id",
            "action",
            "resource_type",
            "resource_id",
            "before",
            "after",
            "ip_address",
            "user_agent",
            "request_id",
            "correlation_id",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class AuditDataAccessLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditDataAccessLog
        fields = [
            "id",
            "actor_type",
            "actor_id",
            "resource_type",
            "resource_id",
            "access_type",
            "field_names",
            "reason",
            "request_id",
            "correlation_id",
            "ip_address",
            "user_agent",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class AuditSecurityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditSecurityEvent
        fields = [
            "id",
            "event_type",
            "severity",
            "actor_type",
            "actor_id",
            "ip_address",
            "user_agent",
            "request_id",
            "correlation_id",
            "description",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class AuditAIDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditAIDecision
        fields = [
            "id",
            "ai_run_id",
            "purpose",
            "provider",
            "model",
            "prompt_version_id",
            "decision_type",
            "decision",
            "risk_level",
            "confidence",
            "input_summary",
            "output_summary",
            "safety_decision",
            "tool_calls_count",
            "blocked_reason",
            "resource_type",
            "resource_id",
            "conversation_id",
            "contact_id",
            "lead_id",
            "ticket_id",
            "task_id",
            "request_id",
            "correlation_id",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class AuditExternalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditExternalRequest
        fields = [
            "id",
            "provider",
            "service",
            "operation",
            "method",
            "url_host",
            "url_path",
            "status_code",
            "duration_ms",
            "success",
            "error_code",
            "error_message",
            "request_id",
            "correlation_id",
            "resource_type",
            "resource_id",
            "idempotency_key",
            "request_metadata",
            "response_metadata",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields
