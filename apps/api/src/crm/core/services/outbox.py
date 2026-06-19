"""Transactional outbox.

Business code persists its change and the matching event inside one
``transaction.atomic`` block. A Celery worker (or the ``process_outbox``
management command) later picks events with ``SELECT ... FOR UPDATE SKIP
LOCKED``, runs the registered handler and retries with capped exponential
backoff. Events whose lock owner crashed are requeued after a stale timeout.

Future phases register handlers with::

    @register_outbox_handler("conversation.message_received.v1")
    def handle(event: OutboxEvent) -> None: ...
"""

import logging
import uuid
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from crm.core.models import OutboxEvent

logger = logging.getLogger(__name__)

OutboxHandler = Callable[[OutboxEvent], None]

_registry: dict[str, OutboxHandler] = {}


class OutboxHandlerNotRegisteredError(Exception):
    """No handler registered for an event type; the event must not be lost."""


def register_outbox_handler(event_type: str) -> Callable[[OutboxHandler], OutboxHandler]:
    def decorator(handler: OutboxHandler) -> OutboxHandler:
        _registry[event_type] = handler
        return handler

    return decorator


def create_outbox_event(
    *,
    event_type: str,
    payload: dict[str, Any],
    organization_id: uuid.UUID | None = None,
    available_at=None,
) -> OutboxEvent:
    """Persist an outbox event.

    Must be called inside the same ``transaction.atomic`` block as the
    business change so both commit or roll back together.
    """
    return OutboxEvent.objects.create(
        organization_id=organization_id,
        event_type=event_type,
        payload=payload,
        available_at=available_at or timezone.now(),
    )


def requeue_stale_events(*, stale_after_seconds: int | None = None) -> int:
    """Return PROCESSING events whose worker died back to the queue."""
    stale_after = stale_after_seconds or settings.OUTBOX_STALE_LOCK_SECONDS
    threshold = timezone.now() - timedelta(seconds=stale_after)
    requeued = OutboxEvent.all_objects.filter(
        status=OutboxEvent.Status.PROCESSING,
        locked_at__lt=threshold,
    ).update(status=OutboxEvent.Status.PENDING, locked_at=None, updated_at=timezone.now())
    if requeued:
        logger.warning(
            "Requeued stale outbox events",
            extra={"event": "outbox.requeued_stale", "metadata": {"count": requeued}},
        )
    return requeued


def lock_pending_events(*, limit: int = 100) -> list[OutboxEvent]:
    """Claim a batch of due events.

    The claim transaction is short on purpose: rows are marked PROCESSING and
    the row locks are released before handlers run, so slow handlers never
    hold database locks. ``skip_locked`` lets concurrent workers claim
    disjoint batches.
    """
    now = timezone.now()
    with transaction.atomic():
        events = list(
            OutboxEvent.all_objects.select_for_update(skip_locked=True)
            .filter(
                status__in=[OutboxEvent.Status.PENDING, OutboxEvent.Status.FAILED],
                available_at__lte=now,
            )
            .order_by("available_at", "created_at")[:limit]
        )
        if events:
            OutboxEvent.all_objects.filter(id__in=[event.id for event in events]).update(
                status=OutboxEvent.Status.PROCESSING, locked_at=now, updated_at=now
            )
            for event in events:
                event.status = OutboxEvent.Status.PROCESSING
                event.locked_at = now
        return events


def process_outbox_batch(
    *,
    handlers: dict[str, OutboxHandler] | None = None,
    limit: int = 100,
    max_attempts: int | None = None,
) -> int:
    """Process due events; returns the number successfully handled.

    ``handlers`` overrides the registry (used by tests). Most outbox events are
    fire-and-forget audit/projection markers with no side-effect handler; an
    event without a registered handler is therefore treated as a successful
    no-op (logged) rather than failing forever — otherwise the whole audit
    stream would dead-letter. Events that DO need a side effect register an
    explicit handler; only an exception raised *by a handler* fails+retries.
    """
    active_handlers = _registry if handlers is None else handlers
    max_attempts = max_attempts or settings.OUTBOX_MAX_ATTEMPTS
    requeue_stale_events()

    processed = 0
    for event in lock_pending_events(limit=limit):
        log_context = {
            "organization_id": str(event.organization_id) if event.organization_id else None,
            "metadata": {"outbox_event_id": str(event.id), "event_type": event.event_type},
        }
        handler = active_handlers.get(event.event_type)
        if handler is None:
            # No side-effect handler: complete as a no-op (it remains in the
            # OutboxEvent table as the durable audit record).
            event.mark_processed()
            processed += 1
            logger.debug(
                "Outbox event has no handler; no-op",
                extra={"event": "outbox.no_handler", **log_context},
            )
            continue
        try:
            handler(event)
            event.mark_processed()
            processed += 1
            logger.info(
                "Outbox event processed", extra={"event": "outbox.processed", **log_context}
            )
        except Exception as exc:
            event.mark_failed(exc, max_attempts=max_attempts)
            logger.exception("Outbox event failed", extra={"event": "outbox.failed", **log_context})
    return processed
