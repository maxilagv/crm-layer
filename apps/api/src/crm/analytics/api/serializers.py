from rest_framework import serializers

from crm.analytics.models import AlertDefinition, AlertEvent, AnalyticsAICostSnapshot


class AnalyticsDashboardSerializer(serializers.Serializer):
    period = serializers.DictField()
    totals = serializers.DictField()
    funnel = serializers.DictField()
    ai_costs = serializers.DictField()
    generated_at = serializers.CharField()


class AnalyticsMetricResponseSerializer(serializers.Serializer):
    period = serializers.DictField()
    metrics = serializers.DictField()


class AnalyticsAICostSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsAICostSnapshot
        fields = [
            "id",
            "date",
            "provider",
            "model",
            "purpose",
            "currency",
            "estimated_cost",
            "input_tokens",
            "output_tokens",
            "cached_tokens",
            "audio_seconds",
            "image_count",
            "run_count",
        ]
        read_only_fields = fields


class AlertDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertDefinition
        fields = [
            "id",
            "name",
            "metric_name",
            "severity",
            "threshold_operator",
            "threshold_value",
            "window_minutes",
            "cooldown_minutes",
            "runbook_path",
            "is_enabled",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class AlertEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertEvent
        fields = [
            "id",
            "name",
            "metric_name",
            "metric_value",
            "threshold_value",
            "severity",
            "status",
            "runbook_path",
            "opened_at",
            "resolved_at",
            "fingerprint",
            "metadata",
        ]
        read_only_fields = fields
