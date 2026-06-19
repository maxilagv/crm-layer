"""Read-side queries for outbox events. Mutations live in services."""

import uuid

from django.db.models import QuerySet
from django.utils import timezone

from crm.core.models import OutboxEvent


def due_events(*, organization_id: uuid.UUID | None = None) -> QuerySet[OutboxEvent]:
    queryset = OutboxEvent.objects.filter(
        status__in=[OutboxEvent.Status.PENDING, OutboxEvent.Status.FAILED],
        available_at__lte=timezone.now(),
    )
    if organization_id is not None:
        queryset = queryset.filter(organization_id=organization_id)
    return queryset


def dead_letter_events(*, organization_id: uuid.UUID | None = None) -> QuerySet[OutboxEvent]:
    queryset = OutboxEvent.objects.filter(status=OutboxEvent.Status.DEAD_LETTER)
    if organization_id is not None:
        queryset = queryset.filter(organization_id=organization_id)
    return queryset
