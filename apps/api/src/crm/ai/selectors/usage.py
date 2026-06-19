"""Aggregated usage/cost queries powering the usage endpoints."""

from django.db.models import Count, DecimalField, Sum
from django.db.models.functions import Coalesce, TruncDate

from crm.ai.models import AIUsageRecord

_ZERO = DecimalField(max_digits=12, decimal_places=6)


def _base(organization, since=None):
    queryset = AIUsageRecord.objects.filter(organization_id=organization.id)
    if since is not None:
        queryset = queryset.filter(created_at__gte=since)
    return queryset


def usage_totals(organization, *, since=None) -> dict:
    return _base(organization, since).aggregate(
        total_cost=Coalesce(Sum("estimated_cost"), 0, output_field=_ZERO),
        input_tokens=Coalesce(Sum("input_tokens"), 0),
        output_tokens=Coalesce(Sum("output_tokens"), 0),
        runs=Count("id"),
    )


def usage_by_purpose(organization, *, since=None) -> list[dict]:
    return list(
        _base(organization, since)
        .values("purpose")
        .annotate(
            total_cost=Coalesce(Sum("estimated_cost"), 0, output_field=_ZERO),
            input_tokens=Coalesce(Sum("input_tokens"), 0),
            output_tokens=Coalesce(Sum("output_tokens"), 0),
            runs=Count("id"),
        )
        .order_by("-total_cost")
    )


def usage_by_model(organization, *, since=None) -> list[dict]:
    return list(
        _base(organization, since)
        .values("provider", "model")
        .annotate(
            total_cost=Coalesce(Sum("estimated_cost"), 0, output_field=_ZERO),
            runs=Count("id"),
        )
        .order_by("-total_cost")
    )


def usage_by_day(organization, *, since=None) -> list[dict]:
    return list(
        _base(organization, since)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            total_cost=Coalesce(Sum("estimated_cost"), 0, output_field=_ZERO),
            runs=Count("id"),
        )
        .order_by("day")
    )
