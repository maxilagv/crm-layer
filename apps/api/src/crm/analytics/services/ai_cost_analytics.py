from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, Sum

from crm.ai.models import AIUsageRecord
from crm.analytics.models import AnalyticsAICostSnapshot
from crm.analytics.services.time import day_bounds


class AICostAnalytics:
    @staticmethod
    def calculate_for_day(*, organization, date) -> list[AnalyticsAICostSnapshot]:
        start, end = day_bounds(date)
        rows = (
            AIUsageRecord.objects.filter(
                organization_id=organization.id,
                created_at__gte=start,
                created_at__lt=end,
            )
            .values("provider", "model", "purpose", "currency")
            .annotate(
                estimated_cost_sum=Sum("estimated_cost"),
                input_tokens_sum=Sum("input_tokens"),
                output_tokens_sum=Sum("output_tokens"),
                cached_tokens_sum=Sum("cached_tokens"),
                audio_seconds_sum=Sum("audio_seconds"),
                image_count_sum=Sum("image_count"),
                run_count=Count("ai_run_id", distinct=True),
            )
        )
        snapshots = []
        seen_keys = set()
        for row in rows:
            key = (row["provider"], row["model"], row["purpose"], row["currency"])
            seen_keys.add(key)
            snapshot, _created = AnalyticsAICostSnapshot.objects.update_or_create(
                organization_id=organization.id,
                date=date,
                provider=row["provider"],
                model=row["model"],
                purpose=row["purpose"],
                currency=row["currency"],
                defaults={
                    "estimated_cost": row["estimated_cost_sum"] or Decimal("0"),
                    "input_tokens": row["input_tokens_sum"] or 0,
                    "output_tokens": row["output_tokens_sum"] or 0,
                    "cached_tokens": row["cached_tokens_sum"] or 0,
                    "audio_seconds": row["audio_seconds_sum"] or Decimal("0"),
                    "image_count": row["image_count_sum"] or 0,
                    "run_count": row["run_count"] or 0,
                },
            )
            snapshots.append(snapshot)
        if not seen_keys:
            AnalyticsAICostSnapshot.objects.filter(
                organization_id=organization.id,
                date=date,
            ).delete()
        return snapshots

    @staticmethod
    def totals_for_period(*, organization, start_date, end_date) -> dict:
        rows = (
            AnalyticsAICostSnapshot.objects.filter(
                organization_id=organization.id,
                date__gte=start_date,
                date__lte=end_date,
            )
            .values("provider", "model", "purpose", "currency")
            .annotate(
                estimated_cost=Sum("estimated_cost"),
                input_tokens=Sum("input_tokens"),
                output_tokens=Sum("output_tokens"),
                cached_tokens=Sum("cached_tokens"),
                audio_seconds=Sum("audio_seconds"),
                image_count=Sum("image_count"),
                run_count=Sum("run_count"),
            )
            .order_by("provider", "model", "purpose")
        )
        return {"items": [_coerce_cost_row(row) for row in rows]}


def _coerce_cost_row(row: dict) -> dict:
    return {
        "provider": row["provider"],
        "model": row["model"],
        "purpose": row["purpose"],
        "currency": row["currency"],
        "estimated_cost": str(row["estimated_cost"] or Decimal("0")),
        "input_tokens": int(row["input_tokens"] or 0),
        "output_tokens": int(row["output_tokens"] or 0),
        "cached_tokens": int(row["cached_tokens"] or 0),
        "audio_seconds": str(row["audio_seconds"] or Decimal("0")),
        "image_count": int(row["image_count"] or 0),
        "run_count": int(row["run_count"] or 0),
    }
