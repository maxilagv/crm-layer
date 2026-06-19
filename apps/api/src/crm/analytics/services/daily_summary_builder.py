from __future__ import annotations

from crm.analytics.models import AnalyticsDailySummary
from crm.analytics.services.metric_collector import MetricCollector
from crm.analytics.services.snapshot_builder import MetricSnapshotWriter


class DailySummaryBuilder:
    @staticmethod
    def build(*, organization, date) -> AnalyticsDailySummary:
        metrics = MetricCollector.collect_for_day(organization=organization, date=date)
        summary, _created = AnalyticsDailySummary.objects.update_or_create(
            organization_id=organization.id,
            date=date,
            defaults={"metrics": metrics},
        )
        MetricSnapshotWriter.upsert_many(
            organization_id=organization.id, date=date, metrics=metrics
        )
        return summary
