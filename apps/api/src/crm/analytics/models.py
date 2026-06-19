from decimal import Decimal

from django.db import models

from crm.core.models import BaseModel

from .domain.enums import (
    AlertSeverity,
    AlertStatus,
    AnalyticsEventSource,
    ThresholdOperator,
)


class AnalyticsEvent(BaseModel):
    event_name = models.CharField(max_length=160)
    source = models.CharField(
        max_length=32, choices=AnalyticsEventSource.choices, default=AnalyticsEventSource.SYSTEM
    )
    occurred_at = models.DateTimeField(db_index=True)
    value = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("1"))
    dimensions = models.JSONField(default=dict, blank=True)
    metric_values = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=128, blank=True)
    correlation_id = models.CharField(max_length=128, blank=True)
    resource_type = models.CharField(max_length=120, blank=True)
    resource_id = models.CharField(max_length=120, blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "analytics_event"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "event_name", "idempotency_key"],
                condition=models.Q(idempotency_key__gt=""),
                name="uniq_analytics_event_org_name_idempotency",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["organization_id", "event_name", "occurred_at"]),
            models.Index(fields=["organization_id", "source", "occurred_at"]),
            models.Index(fields=["request_id"]),
            models.Index(fields=["correlation_id"]),
            models.Index(fields=["occurred_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_name}:{self.occurred_at}"


class AnalyticsMetricSnapshot(BaseModel):
    date = models.DateField(db_index=True)
    metric_name = models.CharField(max_length=160)
    value = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    dimensions = models.JSONField(default=dict, blank=True)
    dimensions_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "analytics_metric_snapshot"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "date", "metric_name", "dimensions_hash"],
                name="uniq_analytics_metric_snapshot",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["organization_id", "date"]),
            models.Index(fields=["organization_id", "metric_name", "date"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.date}:{self.metric_name}:{self.value}"


class AnalyticsDailySummary(BaseModel):
    date = models.DateField(db_index=True)
    metrics = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "analytics_daily_summary"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "date"], name="uniq_analytics_daily_summary"
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["organization_id", "date"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"summary:{self.organization_id}:{self.date}"


class AnalyticsAICostSnapshot(BaseModel):
    date = models.DateField(db_index=True)
    provider = models.CharField(max_length=64)
    model = models.CharField(max_length=120)
    purpose = models.CharField(max_length=64)
    currency = models.CharField(max_length=8, default="USD")
    estimated_cost = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    input_tokens = models.PositiveBigIntegerField(default=0)
    output_tokens = models.PositiveBigIntegerField(default=0)
    cached_tokens = models.PositiveBigIntegerField(default=0)
    audio_seconds = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    image_count = models.PositiveIntegerField(default=0)
    run_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "analytics_ai_cost_snapshot"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "date", "provider", "model", "purpose", "currency"],
                name="uniq_analytics_ai_cost_snapshot",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["organization_id", "date"]),
            models.Index(fields=["organization_id", "provider", "model"]),
            models.Index(fields=["organization_id", "purpose", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.date}:{self.provider}:{self.model}:{self.estimated_cost}"


class AnalyticsFunnelSnapshot(BaseModel):
    date = models.DateField(db_index=True)
    stage_counts = models.JSONField(default=dict, blank=True)
    status_counts = models.JSONField(default=dict, blank=True)
    score_distribution = models.JSONField(default=dict, blank=True)
    totals = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "analytics_funnel_snapshot"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "date"], name="uniq_analytics_funnel_snapshot"
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["organization_id", "date"]),
        ]

    def __str__(self) -> str:
        return f"funnel:{self.organization_id}:{self.date}"


class AnalyticsDashboardSnapshot(BaseModel):
    date = models.DateField(db_index=True)
    period_start = models.DateField()
    period_end = models.DateField()
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "analytics_dashboard_snapshot"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "date", "period_start", "period_end"],
                name="uniq_analytics_dashboard_snapshot",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["organization_id", "date"]),
            models.Index(fields=["organization_id", "period_start", "period_end"]),
        ]

    def __str__(self) -> str:
        return f"dashboard:{self.organization_id}:{self.date}"


class AlertDefinition(BaseModel):
    name = models.CharField(max_length=160)
    metric_name = models.CharField(max_length=160)
    severity = models.CharField(max_length=16, choices=AlertSeverity.choices)
    threshold_operator = models.CharField(
        max_length=8, choices=ThresholdOperator.choices, default=ThresholdOperator.GTE
    )
    threshold_value = models.DecimalField(max_digits=18, decimal_places=6)
    window_minutes = models.PositiveIntegerField(default=15)
    cooldown_minutes = models.PositiveIntegerField(default=60)
    runbook_path = models.CharField(max_length=255)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        db_table = "analytics_alert_definition"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "name"],
                name="uniq_alert_definition_org_name",
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["organization_id", "metric_name", "is_enabled"]),
            models.Index(fields=["organization_id", "severity"]),
        ]

    def __str__(self) -> str:
        return self.name


class AlertEvent(BaseModel):
    definition = models.ForeignKey(
        AlertDefinition, on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    name = models.CharField(max_length=160)
    metric_name = models.CharField(max_length=160)
    metric_value = models.DecimalField(max_digits=18, decimal_places=6)
    threshold_value = models.DecimalField(max_digits=18, decimal_places=6)
    severity = models.CharField(max_length=16, choices=AlertSeverity.choices)
    status = models.CharField(max_length=16, choices=AlertStatus.choices, default=AlertStatus.OPEN)
    runbook_path = models.CharField(max_length=255)
    opened_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    fingerprint = models.CharField(max_length=255)

    class Meta:
        db_table = "analytics_alert_event"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "fingerprint"],
                condition=models.Q(status=AlertStatus.OPEN),
                name="uniq_open_alert_event_fingerprint",
            )
        ]
        indexes = [
            models.Index(fields=["organization_id", "deleted_at"]),
            models.Index(fields=["organization_id", "status", "opened_at"]),
            models.Index(fields=["organization_id", "severity", "opened_at"]),
            models.Index(fields=["fingerprint"]),
        ]

    def __str__(self) -> str:
        return f"{self.name}:{self.status}"
