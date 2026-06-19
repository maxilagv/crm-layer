import pytest
from django.utils import timezone

from crm.analytics.models import (
    AlertDefinition,
    AlertEvent,
    AnalyticsAICostSnapshot,
    AnalyticsDailySummary,
)
from crm.analytics.tasks import (
    build_dashboard_snapshot,
    calculate_ai_costs,
    check_alerts,
    collect_daily_metrics,
)
from tests.factories.ai import AIUsageRecordFactory
from tests.factories.conversations import MessageFactory
from tests.factories.organizations import OrganizationFactory
from tests.factories.tasks import TaskFactory


@pytest.mark.django_db
def test_collect_daily_metrics_idempotent() -> None:
    organization = OrganizationFactory()
    MessageFactory(organization_id=organization.id, direction="inbound")
    TaskFactory(organization_id=organization.id)

    first = collect_daily_metrics.run(organization_id=str(organization.id))
    second = collect_daily_metrics.run(organization_id=str(organization.id))

    assert first["metrics"]["messages_received_total"] == 1
    assert second["metrics"]["tasks_created_total"] == 1
    assert AnalyticsDailySummary.objects.filter(organization_id=organization.id).count() == 1


@pytest.mark.django_db
def test_calculate_ai_costs_idempotent() -> None:
    organization = OrganizationFactory()
    AIUsageRecordFactory(organization_id=organization.id)

    calculate_ai_costs.run(organization_id=str(organization.id))
    calculate_ai_costs.run(organization_id=str(organization.id))

    snapshot = AnalyticsAICostSnapshot.objects.get(organization_id=organization.id)
    assert snapshot.estimated_cost > 0
    assert snapshot.run_count == 1


@pytest.mark.django_db
def test_build_dashboard_snapshot_idempotent() -> None:
    organization = OrganizationFactory()

    first = build_dashboard_snapshot.run(organization_id=str(organization.id))
    second = build_dashboard_snapshot.run(organization_id=str(organization.id))

    assert first["snapshot_id"] == second["snapshot_id"]


@pytest.mark.django_db
def test_check_alerts_creates_alert_with_runbook() -> None:
    organization = OrganizationFactory()
    day = timezone.localdate()
    AnalyticsDailySummary.objects.create(
        organization_id=organization.id,
        date=day,
        metrics={"whatsapp_failures_total": 10},
    )
    from crm.analytics.services.snapshot_builder import MetricSnapshotWriter

    MetricSnapshotWriter.upsert(
        organization_id=organization.id,
        date=day,
        metric_name="whatsapp_failures_total",
        value=10,
    )

    result = check_alerts.run(organization_id=str(organization.id), date=day.isoformat())

    assert result["opened"] == 1
    event = AlertEvent.objects.get(organization_id=organization.id)
    assert event.runbook_path.endswith("whatsapp-webhook-failing.md")
    assert AlertDefinition.objects.filter(organization_id=organization.id).exists()
