from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from crm.analytics.models import AnalyticsEvent
from crm.audit.services import sanitize_payload
from crm.core.observability.context import get_correlation_id, get_request_id


class AnalyticsEventCollector:
    @staticmethod
    def record(
        *,
        organization,
        event_name: str,
        source: str = "system",
        value: Decimal | int | str = Decimal("1"),
        dimensions: dict | None = None,
        metric_values: dict | None = None,
        occurred_at=None,
        request=None,
        resource_type: str = "",
        resource_id: str = "",
        idempotency_key: str = "",
        metadata: dict | None = None,
    ) -> AnalyticsEvent:
        request_id = (
            getattr(request, "request_id", "") if request is not None else get_request_id() or ""
        )
        correlation_id = (
            getattr(request, "correlation_id", "")
            if request is not None
            else get_correlation_id() or ""
        )
        event, _created = AnalyticsEvent.objects.get_or_create(
            organization_id=getattr(organization, "id", organization),
            event_name=event_name,
            idempotency_key=idempotency_key,
            defaults={
                "source": source,
                "occurred_at": occurred_at or timezone.now(),
                "value": Decimal(str(value)),
                "dimensions": sanitize_payload(dimensions or {}),
                "metric_values": sanitize_payload(metric_values or {}),
                "request_id": request_id,
                "correlation_id": correlation_id,
                "resource_type": resource_type,
                "resource_id": str(resource_id) if resource_id else "",
                "metadata": sanitize_payload(metadata or {}),
            },
        )
        return event
