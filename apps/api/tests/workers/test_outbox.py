from datetime import timedelta

import pytest
from django.utils import timezone

from crm.core.models import OutboxEvent
from crm.core.services.outbox import (
    create_outbox_event,
    process_outbox_batch,
    requeue_stale_events,
)
from tests.factories.core import OutboxEventFactory


@pytest.mark.django_db
def test_outbox_event_creation() -> None:
    event = create_outbox_event(
        event_type="test.event.v1",
        payload={"id": "123"},
    )

    assert event.status == OutboxEvent.Status.PENDING
    assert event.payload == {"id": "123"}
    assert event.attempts == 0


@pytest.mark.django_db
def test_outbox_event_processing_marks_processed() -> None:
    event = create_outbox_event(event_type="test.event.v1", payload={"id": "123"})
    calls = []

    processed = process_outbox_batch(
        handlers={"test.event.v1": lambda item: calls.append(str(item.id))},
    )
    event.refresh_from_db()

    assert processed == 1
    assert calls == [str(event.id)]
    assert event.status == OutboxEvent.Status.PROCESSED
    assert event.processed_at is not None


@pytest.mark.django_db
def test_outbox_event_failure_and_retry_without_duplicate_processing() -> None:
    event = create_outbox_event(event_type="test.fail.v1", payload={"id": "123"})

    def failing_handler(_event):
        raise RuntimeError("temporary failure")

    processed = process_outbox_batch(handlers={"test.fail.v1": failing_handler})
    event.refresh_from_db()

    assert processed == 0
    assert event.status == OutboxEvent.Status.FAILED
    assert event.attempts == 1
    assert "temporary failure" in event.error_message
    assert event.available_at > timezone.now()  # retry is delayed with backoff

    OutboxEvent.all_objects.filter(id=event.id).update(available_at=timezone.now())
    processed_again = process_outbox_batch(handlers={"test.fail.v1": lambda _event: None})
    event.refresh_from_db()

    assert processed_again == 1
    assert event.status == OutboxEvent.Status.PROCESSED
    assert event.attempts == 1


@pytest.mark.django_db
def test_outbox_event_without_handler_is_noop() -> None:
    # Most events are fire-and-forget audit markers: with no registered handler they
    # complete as a no-op (the row stays as the durable audit record), never dead-letter.
    event = create_outbox_event(event_type="test.unknown.v1", payload={})

    processed = process_outbox_batch(handlers={})
    event.refresh_from_db()

    assert processed == 1
    assert event.status == OutboxEvent.Status.PROCESSED


@pytest.mark.django_db
def test_outbox_event_dead_letters_after_max_attempts() -> None:
    event = create_outbox_event(event_type="test.fail.v1", payload={})

    def failing_handler(_event):
        raise RuntimeError("permanent failure")

    process_outbox_batch(handlers={"test.fail.v1": failing_handler}, max_attempts=1)
    event.refresh_from_db()

    assert event.status == OutboxEvent.Status.DEAD_LETTER
    assert event.attempts == 1

    # Dead-lettered events are never picked up again.
    processed = process_outbox_batch(handlers={"test.fail.v1": lambda _event: None})
    assert processed == 0


@pytest.mark.django_db
def test_stale_processing_events_are_requeued() -> None:
    event = OutboxEventFactory(
        status=OutboxEvent.Status.PROCESSING,
        locked_at=timezone.now() - timedelta(hours=1),
    )
    fresh = OutboxEventFactory(
        status=OutboxEvent.Status.PROCESSING,
        locked_at=timezone.now(),
    )

    requeued = requeue_stale_events(stale_after_seconds=300)
    event.refresh_from_db()
    fresh.refresh_from_db()

    assert requeued == 1
    assert event.status == OutboxEvent.Status.PENDING
    assert event.locked_at is None
    assert fresh.status == OutboxEvent.Status.PROCESSING
