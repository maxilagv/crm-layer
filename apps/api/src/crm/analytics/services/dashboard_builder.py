from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from crm.analytics.models import AnalyticsDailySummary, AnalyticsDashboardSnapshot
from crm.analytics.services.ai_cost_analytics import AICostAnalytics
from crm.analytics.services.daily_summary_builder import DailySummaryBuilder
from crm.analytics.services.funnel_analytics import FunnelAnalytics
from crm.analytics.services.time import default_period, iter_days


class DashboardBuilder:
    @staticmethod
    def build(*, organization, start_date=None, end_date=None) -> dict:
        start_date, end_date = _period(start_date, end_date)
        for day in iter_days(start_date, end_date):
            DailySummaryBuilder.build(organization=organization, date=day)
            AICostAnalytics.calculate_for_day(organization=organization, date=day)
        funnel = FunnelAnalytics.build_for_day(organization=organization, date=end_date)
        summaries = AnalyticsDailySummary.objects.filter(
            organization_id=organization.id, date__gte=start_date, date__lte=end_date
        )
        totals = _aggregate_summary_metrics(summaries)
        ai_costs = AICostAnalytics.totals_for_period(
            organization=organization, start_date=start_date, end_date=end_date
        )
        payload = {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "totals": totals,
            "funnel": {
                "stage_counts": funnel.stage_counts,
                "status_counts": funnel.status_counts,
                "score_distribution": funnel.score_distribution,
                "totals": funnel.totals,
            },
            "ai_costs": ai_costs,
            "generated_at": timezone.now().isoformat(),
        }
        return payload

    @staticmethod
    def snapshot(*, organization, start_date=None, end_date=None) -> AnalyticsDashboardSnapshot:
        start_date, end_date = _period(start_date, end_date)
        payload = DashboardBuilder.build(
            organization=organization, start_date=start_date, end_date=end_date
        )
        snapshot, _created = AnalyticsDashboardSnapshot.objects.update_or_create(
            organization_id=organization.id,
            date=end_date,
            period_start=start_date,
            period_end=end_date,
            defaults={"payload": payload},
        )
        return snapshot


def _period(start_date, end_date):
    if start_date and end_date:
        return start_date, end_date
    return default_period()


def _aggregate_summary_metrics(summaries) -> dict:
    totals: dict[str, Decimal] = {}
    weighted_resolution_seconds = Decimal("0")
    resolved_count = Decimal("0")
    for summary in summaries:
        metrics = summary.metrics or {}
        for key, value in metrics.items():
            if key == "average_resolution_time_seconds":
                ticket_count = Decimal(str(metrics.get("tickets_resolved_total", 0) or 0))
                weighted_resolution_seconds += Decimal(str(value or 0)) * ticket_count
                resolved_count += ticket_count
                continue
            try:
                totals[key] = totals.get(key, Decimal("0")) + Decimal(str(value or 0))
            except Exception:
                continue
    if resolved_count:
        totals["average_resolution_time_seconds"] = (
            weighted_resolution_seconds / resolved_count
        ).quantize(Decimal("0.01"))
    else:
        totals["average_resolution_time_seconds"] = Decimal("0")
    return {key: _json_number(value) for key, value in totals.items()}


def _json_number(value: Decimal):
    if value == value.to_integral_value():
        return int(value)
    return str(value)
