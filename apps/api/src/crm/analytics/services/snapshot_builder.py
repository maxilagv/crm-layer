from __future__ import annotations

import hashlib
import json
from decimal import Decimal

from crm.analytics.models import AnalyticsMetricSnapshot


def dimensions_hash(dimensions: dict) -> str:
    raw = json.dumps(dimensions or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


class MetricSnapshotWriter:
    @staticmethod
    def upsert(
        *,
        organization_id,
        date,
        metric_name: str,
        value,
        dimensions: dict | None = None,
    ) -> AnalyticsMetricSnapshot:
        dimensions = dimensions or {}
        snapshot, _created = AnalyticsMetricSnapshot.objects.update_or_create(
            organization_id=organization_id,
            date=date,
            metric_name=metric_name,
            dimensions_hash=dimensions_hash(dimensions),
            defaults={
                "value": Decimal(str(value or 0)),
                "dimensions": dimensions,
            },
        )
        return snapshot

    @classmethod
    def upsert_many(cls, *, organization_id, date, metrics: dict) -> int:
        count = 0
        for metric_name, value in metrics.items():
            if isinstance(value, dict):
                continue
            cls.upsert(
                organization_id=organization_id,
                date=date,
                metric_name=metric_name,
                value=value,
            )
            count += 1
        return count
