from datetime import date as date_cls

from celery import shared_task
from django.utils import timezone


@shared_task(name="analytics.collect_daily_metrics", ignore_result=False)
def collect_daily_metrics(*, organization_id: str, date: str | None = None):
    from crm.analytics.services.daily_summary_builder import DailySummaryBuilder
    from crm.organizations.models import Organization

    organization = Organization.objects.get(id=organization_id)
    day = date_cls.fromisoformat(date) if date else timezone.localdate()
    summary = DailySummaryBuilder.build(organization=organization, date=day)
    return {"date": summary.date.isoformat(), "metrics": summary.metrics}


@shared_task(name="analytics.build_dashboard_snapshot", ignore_result=False)
def build_dashboard_snapshot(
    *, organization_id: str, start_date: str | None = None, end_date: str | None = None
):
    from django.utils.dateparse import parse_date

    from crm.analytics.services.dashboard_builder import DashboardBuilder
    from crm.organizations.models import Organization

    organization = Organization.objects.get(id=organization_id)
    snapshot = DashboardBuilder.snapshot(
        organization=organization,
        start_date=parse_date(start_date) if start_date else None,
        end_date=parse_date(end_date) if end_date else None,
    )
    return {"snapshot_id": str(snapshot.id), "date": snapshot.date.isoformat()}


@shared_task(name="analytics.calculate_ai_costs", ignore_result=False)
def calculate_ai_costs(*, organization_id: str, date: str | None = None):
    from crm.analytics.services.ai_cost_analytics import AICostAnalytics
    from crm.organizations.models import Organization

    organization = Organization.objects.get(id=organization_id)
    day = date_cls.fromisoformat(date) if date else timezone.localdate()
    snapshots = AICostAnalytics.calculate_for_day(organization=organization, date=day)
    return {"date": day.isoformat(), "snapshots": len(snapshots)}


@shared_task(name="analytics.check_alerts", ignore_result=False)
def check_alerts(*, organization_id: str, date: str | None = None):
    from crm.analytics.services.alert_service import AlertService
    from crm.organizations.models import Organization

    organization = Organization.objects.get(id=organization_id)
    day = date_cls.fromisoformat(date) if date else timezone.localdate()
    events = AlertService.check_alerts(organization=organization, date=day)
    return {"date": day.isoformat(), "opened": len(events)}
