"""Cost/health queries over AIRun (failed runs, safety blocks)."""

from django.db.models import Count, QuerySet

from crm.ai.domain.enums import AIRunStatus
from crm.ai.models import AIRun


def failed_runs(organization, *, since=None) -> QuerySet[AIRun]:
    queryset = AIRun.objects.filter(
        organization_id=organization.id,
        status__in=[AIRunStatus.FAILED, AIRunStatus.SCHEMA_INVALID],
    )
    if since is not None:
        queryset = queryset.filter(created_at__gte=since)
    return queryset.order_by("-created_at")


def safety_blocked_runs(organization, *, since=None) -> QuerySet[AIRun]:
    queryset = AIRun.objects.filter(
        organization_id=organization.id, status=AIRunStatus.BLOCKED_BY_SAFETY
    )
    if since is not None:
        queryset = queryset.filter(created_at__gte=since)
    return queryset.order_by("-created_at")


def status_breakdown(organization, *, since=None) -> list[dict]:
    queryset = AIRun.objects.filter(organization_id=organization.id)
    if since is not None:
        queryset = queryset.filter(created_at__gte=since)
    return list(queryset.values("status").annotate(count=Count("id")).order_by("-count"))
