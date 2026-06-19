"""Read-side queries for idempotency keys. Mutations live in services."""

import uuid

from crm.core.models import IdempotencyKey


def find_record(
    *, key: str, scope: str, organization_id: uuid.UUID | None = None
) -> IdempotencyKey | None:
    return IdempotencyKey.objects.filter(
        organization_id=organization_id, scope=scope, key=key
    ).first()
