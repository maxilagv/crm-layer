"""Reusable idempotency primitives.

Intended consumers: mutable HTTP endpoints, WhatsApp webhooks, retryable
Celery jobs, outbound sends, media downloads and AI generation. The flow is:

    result = start_idempotent_operation(key=..., scope=..., request_hash=...)
    if result.replay:
        return result.record.response_body, result.record.status_code
    ...do the work...
    complete_idempotent_operation(result.record, response_body=..., status_code=...)
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from crm.core.models import IdempotencyKey

DEFAULT_TTL = timedelta(hours=24)


class IdempotencyConflictError(Exception):
    """Same idempotency key reused with a different request payload."""


@dataclass(frozen=True)
class IdempotencyStartResult:
    record: IdempotencyKey
    created: bool
    replay: bool


def build_request_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _locked_record(
    *, organization_id: uuid.UUID | None, scope: str, key: str
) -> IdempotencyKey | None:
    return (
        IdempotencyKey.all_objects.select_for_update()
        .filter(organization_id=organization_id, scope=scope, key=key)
        .first()
    )


def start_idempotent_operation(
    *,
    key: str,
    scope: str,
    request_hash: str,
    organization_id: uuid.UUID | None = None,
    ttl: timedelta = DEFAULT_TTL,
) -> IdempotencyStartResult:
    """Start or reuse an idempotent operation under a row lock.

    Concurrency-safe: two simultaneous calls with the same new key race on the
    unique constraint; the loser recovers the winner's row instead of failing.
    """
    expires_at = timezone.now() + ttl

    with transaction.atomic():
        record = _locked_record(organization_id=organization_id, scope=scope, key=key)

        if record is None:
            try:
                # Savepoint so a unique-constraint violation does not poison
                # the caller's transaction.
                with transaction.atomic():
                    record = IdempotencyKey.objects.create(
                        organization_id=organization_id,
                        key=key,
                        scope=scope,
                        request_hash=request_hash,
                        expires_at=expires_at,
                    )
                return IdempotencyStartResult(record=record, created=True, replay=False)
            except IntegrityError:
                # A concurrent request inserted the same key first.
                record = _locked_record(organization_id=organization_id, scope=scope, key=key)
                if record is None:  # pragma: no cover - requires a third writer
                    raise

        if record.is_expired():
            # Expired keys restart the operation and accept a new payload.
            record.status = IdempotencyKey.Status.PROCESSING
            record.request_hash = request_hash
            record.response_body = None
            record.status_code = None
            record.expires_at = expires_at
            record.save(
                update_fields=[
                    "status",
                    "request_hash",
                    "response_body",
                    "status_code",
                    "expires_at",
                    "updated_at",
                ]
            )
            return IdempotencyStartResult(record=record, created=False, replay=False)

        if record.request_hash != request_hash:
            raise IdempotencyConflictError("Idempotency key reused with a different request hash")

        return IdempotencyStartResult(
            record=record,
            created=False,
            replay=record.status == IdempotencyKey.Status.COMPLETED,
        )


def complete_idempotent_operation(
    record: IdempotencyKey,
    *,
    response_body: Any,
    status_code: int,
) -> IdempotencyKey:
    with transaction.atomic():
        locked = IdempotencyKey.all_objects.select_for_update().get(id=record.id)
        locked.response_body = response_body
        locked.status_code = status_code
        locked.status = IdempotencyKey.Status.COMPLETED
        locked.save(update_fields=["response_body", "status_code", "status", "updated_at"])
        return locked


def fail_idempotent_operation(
    record: IdempotencyKey,
    *,
    response_body: Any | None = None,
    status_code: int | None = None,
) -> IdempotencyKey:
    with transaction.atomic():
        locked = IdempotencyKey.all_objects.select_for_update().get(id=record.id)
        locked.response_body = response_body
        locked.status_code = status_code
        locked.status = IdempotencyKey.Status.FAILED
        locked.save(update_fields=["response_body", "status_code", "status", "updated_at"])
        return locked
