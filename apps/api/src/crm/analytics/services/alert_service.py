from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from crm.analytics.domain.enums import AlertStatus, ThresholdOperator
from crm.analytics.models import AlertDefinition, AlertEvent, AnalyticsMetricSnapshot

DEFAULT_ALERT_DEFINITIONS = [
    {
        "name": "WhatsApp webhook failing",
        "metric_name": "whatsapp_failures_total",
        "severity": "high",
        "threshold_operator": "gte",
        "threshold_value": "5",
        "window_minutes": 15,
        "cooldown_minutes": 60,
        "runbook_path": "docs/runbooks/whatsapp-webhook-failing.md",
    },
    {
        "name": "AI provider failing",
        "metric_name": "ai_failures_total",
        "severity": "high",
        "threshold_operator": "gte",
        "threshold_value": "3",
        "window_minutes": 15,
        "cooldown_minutes": 60,
        "runbook_path": "docs/runbooks/ai-provider-failing.md",
    },
    {
        "name": "AI cost spike",
        "metric_name": "ai_cost_total",
        "severity": "medium",
        "threshold_operator": "gte",
        "threshold_value": "25",
        "window_minutes": 1440,
        "cooldown_minutes": 720,
        "runbook_path": "docs/runbooks/ai-cost-spike.md",
    },
    {
        "name": "Failed messages spike",
        "metric_name": "failed_messages_total",
        "severity": "high",
        "threshold_operator": "gte",
        "threshold_value": "10",
        "window_minutes": 15,
        "cooldown_minutes": 60,
        "runbook_path": "docs/runbooks/failed-messages-spike.md",
    },
]


class AlertService:
    @staticmethod
    def seed_defaults(*, organization) -> int:
        created = 0
        for definition in DEFAULT_ALERT_DEFINITIONS:
            _, was_created = AlertDefinition.objects.get_or_create(
                organization_id=organization.id,
                name=definition["name"],
                defaults=definition,
            )
            created += int(was_created)
        return created

    @staticmethod
    def check_alerts(*, organization, date=None) -> list[AlertEvent]:
        AlertService.seed_defaults(organization=organization)
        date = date or timezone.localdate()
        opened = []
        for definition in AlertDefinition.objects.filter(
            organization_id=organization.id, is_enabled=True
        ):
            value = _metric_value(organization_id=organization.id, date=date, definition=definition)
            if not _breaches(value, definition.threshold_operator, definition.threshold_value):
                continue
            fingerprint = f"{organization.id}:{definition.name}:{date.isoformat()}"
            if _is_in_cooldown(definition=definition, fingerprint=fingerprint):
                continue
            event, created = AlertEvent.objects.get_or_create(
                organization_id=organization.id,
                fingerprint=fingerprint,
                status=AlertStatus.OPEN.value,
                defaults={
                    "definition": definition,
                    "name": definition.name,
                    "metric_name": definition.metric_name,
                    "metric_value": value,
                    "threshold_value": definition.threshold_value,
                    "severity": definition.severity,
                    "runbook_path": definition.runbook_path,
                    "metadata": {"window_minutes": definition.window_minutes},
                },
            )
            if created:
                opened.append(event)
        return opened


def _metric_value(*, organization_id, date, definition: AlertDefinition) -> Decimal:
    total = AnalyticsMetricSnapshot.objects.filter(
        organization_id=organization_id,
        date=date,
        metric_name=definition.metric_name,
    ).aggregate(value=Sum("value"))["value"] or Decimal("0")
    return Decimal(str(total))


def _breaches(value: Decimal, operator: str, threshold: Decimal) -> bool:
    threshold = Decimal(str(threshold))
    return {
        ThresholdOperator.GT.value: value > threshold,
        ThresholdOperator.GTE.value: value >= threshold,
        ThresholdOperator.LT.value: value < threshold,
        ThresholdOperator.LTE.value: value <= threshold,
        ThresholdOperator.EQ.value: value == threshold,
    }[operator]


def _is_in_cooldown(*, definition: AlertDefinition, fingerprint: str) -> bool:
    cutoff = timezone.now() - timedelta(minutes=definition.cooldown_minutes)
    return AlertEvent.objects.filter(
        organization_id=definition.organization_id,
        fingerprint=fingerprint,
        created_at__gte=cutoff,
    ).exists()
