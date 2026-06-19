import uuid
from datetime import UTC, datetime

import pytest

from crm.core.models import IdempotencyKey


@pytest.mark.django_db
def test_base_model_fields() -> None:
    organization_id = uuid.uuid4()
    record = IdempotencyKey.objects.create(
        organization_id=organization_id,
        key="abc",
        scope="test",
        request_hash="hash",
        metadata={"source": "test"},
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )

    assert record.id
    assert record.organization_id == organization_id
    assert record.created_at
    assert record.updated_at
    assert record.deleted_at is None
    assert record.created_by_id is None
    assert record.updated_by_id is None
    assert record.metadata == {"source": "test"}


@pytest.mark.django_db
def test_soft_delete_excludes_default_manager() -> None:
    record = IdempotencyKey.objects.create(
        key="soft-delete",
        scope="test",
        request_hash="hash",
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )

    record.soft_delete()

    assert not IdempotencyKey.objects.filter(id=record.id).exists()
    assert IdempotencyKey.all_objects.filter(id=record.id).exists()


@pytest.mark.django_db
def test_restore_returns_record_to_default_manager() -> None:
    record = IdempotencyKey.objects.create(
        key="restore",
        scope="test",
        request_hash="hash",
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    record.soft_delete()

    record.restore()

    assert IdempotencyKey.objects.filter(id=record.id).exists()
