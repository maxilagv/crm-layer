from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from crm.analytics.api.permissions import AnalyticsReadPermission
from crm.analytics.api.serializers import (
    AlertDefinitionSerializer,
    AlertEventSerializer,
    AnalyticsAICostSnapshotSerializer,
    AnalyticsDashboardSerializer,
    AnalyticsMetricResponseSerializer,
)
from crm.analytics.models import AlertDefinition
from crm.analytics.selectors.dashboard import (
    ai_cost_snapshots_for_organization,
    open_alerts_for_organization,
)
from crm.analytics.services import AlertService, DashboardBuilder
from crm.analytics.services.ai_cost_analytics import AICostAnalytics
from crm.analytics.services.daily_summary_builder import DailySummaryBuilder
from crm.analytics.services.funnel_analytics import FunnelAnalytics
from crm.analytics.services.time import default_period, iter_days
from crm.core.api.pagination import StandardPagination
from crm.core.api.responses import success_response
from crm.organizations.selectors.organizations import resolve_current_organization


class AnalyticsDashboardView(APIView):
    permission_classes = [AnalyticsReadPermission]

    @extend_schema(responses=AnalyticsDashboardSerializer)
    def get(self, request):
        organization = resolve_current_organization(request)
        start_date, end_date = _period_from_request(request)
        return success_response(
            request,
            DashboardBuilder.build(
                organization=organization,
                start_date=start_date,
                end_date=end_date,
            ),
        )


class _MetricView(APIView):
    permission_classes = [AnalyticsReadPermission]
    metric_names: tuple[str, ...] = ()

    @extend_schema(responses=AnalyticsMetricResponseSerializer)
    def get(self, request):
        organization = resolve_current_organization(request)
        start_date, end_date = _period_from_request(request)
        metrics = {name: 0 for name in self.metric_names}
        for day in iter_days(start_date, end_date):
            summary = DailySummaryBuilder.build(organization=organization, date=day)
            for name in self.metric_names:
                metrics[name] += _number(summary.metrics.get(name, 0))
        return success_response(
            request,
            {
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "metrics": metrics,
            },
        )


class AnalyticsLeadsView(_MetricView):
    metric_names = (
        "leads_created_total",
        "hot_leads_total",
        "calls_requested_total",
        "calls_scheduled_total",
    )


class AnalyticsConversationsView(_MetricView):
    metric_names = ("messages_received_total", "messages_sent_total")


class AnalyticsTasksView(_MetricView):
    metric_names = (
        "tasks_created_total",
        "tasks_completed_total",
        "tasks_overdue_total",
        "reminders_sent_total",
    )


class AnalyticsTicketsView(_MetricView):
    metric_names = (
        "tickets_created_total",
        "tickets_resolved_total",
        "tickets_urgent_total",
        "average_resolution_time_seconds",
        "audio_transcription_failures_total",
    )


class AnalyticsWhatsAppView(_MetricView):
    metric_names = (
        "messages_received_total",
        "messages_sent_total",
        "whatsapp_failures_total",
        "failed_messages_total",
    )


class AnalyticsAICostsView(APIView):
    permission_classes = [AnalyticsReadPermission]

    @extend_schema(responses=AnalyticsAICostSnapshotSerializer(many=True))
    def get(self, request):
        organization = resolve_current_organization(request)
        start_date, end_date = _period_from_request(request)
        for day in iter_days(start_date, end_date):
            AICostAnalytics.calculate_for_day(organization=organization, date=day)
        queryset = ai_cost_snapshots_for_organization(
            organization, start_date=start_date, end_date=end_date
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(
            AnalyticsAICostSnapshotSerializer(page, many=True).data
        )


class AnalyticsFunnelView(APIView):
    permission_classes = [AnalyticsReadPermission]

    @extend_schema(responses={200: dict})
    def get(self, request):
        organization = resolve_current_organization(request)
        _start_date, end_date = _period_from_request(request)
        snapshot = FunnelAnalytics.build_for_day(organization=organization, date=end_date)
        return success_response(
            request,
            {
                "date": snapshot.date.isoformat(),
                "stage_counts": snapshot.stage_counts,
                "status_counts": snapshot.status_counts,
                "score_distribution": snapshot.score_distribution,
                "totals": snapshot.totals,
            },
        )


class AlertDefinitionsView(APIView):
    permission_classes = [AnalyticsReadPermission]

    @extend_schema(responses=AlertDefinitionSerializer(many=True))
    def get(self, request):
        organization = resolve_current_organization(request)
        AlertService.seed_defaults(organization=organization)
        queryset = AlertDefinition.objects.filter(organization_id=organization.id).order_by("name")
        return success_response(request, AlertDefinitionSerializer(queryset, many=True).data)


class AlertEventsView(APIView):
    permission_classes = [AnalyticsReadPermission]

    @extend_schema(responses=AlertEventSerializer(many=True))
    def get(self, request):
        organization = resolve_current_organization(request)
        queryset = open_alerts_for_organization(organization)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(AlertEventSerializer(page, many=True).data)


def _period_from_request(request):
    start_date = parse_date(request.query_params.get("start_date") or "")
    end_date = parse_date(request.query_params.get("end_date") or "")
    if start_date and end_date:
        return start_date, end_date
    return default_period()


def _number(value):
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return 0
    return int(number) if number.is_integer() else number
