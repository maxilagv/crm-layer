from django.db.models import Sum

from crm.analytics.models import (
    AlertEvent,
    AnalyticsAICostSnapshot,
    AnalyticsDailySummary,
    AnalyticsFunnelSnapshot,
)


def daily_summaries_for_organization(organization, *, start_date=None, end_date=None):
    queryset = AnalyticsDailySummary.objects.filter(organization_id=organization.id)
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
    return queryset.order_by("-date")


def latest_funnel_snapshot(organization):
    return (
        AnalyticsFunnelSnapshot.objects.filter(organization_id=organization.id)
        .order_by("-date")
        .first()
    )


def ai_cost_snapshots_for_organization(organization, *, start_date=None, end_date=None):
    queryset = AnalyticsAICostSnapshot.objects.filter(organization_id=organization.id)
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
    return queryset.order_by("-date", "provider", "model", "purpose")


def open_alerts_for_organization(organization):
    return AlertEvent.objects.filter(organization_id=organization.id, status="open").order_by(
        "-opened_at"
    )


def metric_total(organization, metric_name: str, *, start_date=None, end_date=None):
    summaries = daily_summaries_for_organization(
        organization, start_date=start_date, end_date=end_date
    )
    total = 0
    for summary in summaries:
        total += float(summary.metrics.get(metric_name, 0) or 0)
    return total


def ai_cost_total(organization, *, start_date=None, end_date=None):
    queryset = ai_cost_snapshots_for_organization(
        organization, start_date=start_date, end_date=end_date
    )
    return queryset.aggregate(total=Sum("estimated_cost"))["total"] or 0
