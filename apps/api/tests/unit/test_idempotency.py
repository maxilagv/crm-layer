from datetime import timedelta

import pytest
from django.utils import timezone

from crm.core.models import IdempotencyKey
from crm.core.services.idempotency import (
    IdempotencyConflictError,
    build_request_hash,
    complete_idempotent_operation,
    fail_idempotent_operation,
    start_idempotent_operation,
)


@pytest.mark.django_db
def test_idempotency_key_reuse() -> None:
    request_hash = build_request_hash({"amount": 100})

    first = start_idempotent_operation(key="key-1", scope="payments", request_hash=request_hash)
    completed = complete_idempotent_operation(
        first.record,
        response_body={"ok": True},
        status_code=200,
    )
    second = start_idempotent_operation(key="key-1", scope="payments", request_hash=request_hash)

    assert first.created is True
    assert completed.status == IdempotencyKey.Status.COMPLETED
    assert second.created is False
    assert second.replay is True
    assert second.record.response_body == {"ok": True}
    assert second.record.status_code == 200


@pytest.mark.django_db
def test_idempotency_hash_conflict() -> None:
    start_idempotent_operation(
        key="key-2",
        scope="payments",
        request_hash=build_request_hash({"amount": 100}),
    )

    with pytest.raises(IdempotencyConflictError):
        start_idempotent_operation(
            key="key-2",
            scope="payments",
            request_hash=build_request_hash({"amount": 200}),
        )


@pytest.mark.django_db
def test_idempotency_expiration_restarts_operation() -> None:
    request_hash = build_request_hash({"amount": 100})
    result = start_idempotent_operation(
        key="key-3",
        scope="payments",
        request_hash=request_hash,
        ttl=timedelta(seconds=1),
    )
    IdempotencyKey.all_objects.filter(id=result.record.id).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )

    restarted = start_idempotent_operation(
        key="key-3",
        scope="payments",
        request_hash=request_hash,
    )

    assert restarted.created is False
    assert restarted.replay is False
    assert restarted.record.status == IdempotencyKey.Status.PROCESSING


@pytest.mark.django_db
def test_expired_key_accepts_a_new_request_hash() -> None:
    result = start_idempotent_operation(
        key="key-4",
        scope="payments",
        request_hash=build_request_hash({"amount": 100}),
    )
    IdempotencyKey.all_objects.filter(id=result.record.id).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )

    new_hash = build_request_hash({"amount": 999})
    restarted = start_idempotent_operation(key="key-4", scope="payments", request_hash=new_hash)

    assert restarted.replay is False
    assert restarted.record.request_hash == new_hash


@pytest.mark.django_db
def test_same_key_in_different_scopes_does_not_collide() -> None:
    request_hash = build_request_hash({"amount": 100})

    first = start_idempotent_operation(key="key-5", scope="payments", request_hash=request_hash)
    second = start_idempotent_operation(key="key-5", scope="webhooks", request_hash=request_hash)

    assert first.created is True
    assert second.created is True
    assert first.record.id != second.record.id


@pytest.mark.django_db
def test_failed_operation_is_not_replayed() -> None:
    request_hash = build_request_hash({"amount": 100})
    result = start_idempotent_operation(key="key-6", scope="payments", request_hash=request_hash)

    fail_idempotent_operation(result.record, response_body={"error": "boom"}, status_code=500)
    retried = start_idempotent_operation(key="key-6", scope="payments", request_hash=request_hash)

    assert retried.replay is False
    assert retried.record.status == IdempotencyKey.Status.FAILED
