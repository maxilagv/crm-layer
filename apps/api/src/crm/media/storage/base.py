"""Storage adapter interface. All backends store private files only."""

import hashlib
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime

from crm.media.domain.exceptions import UnsafeStorageKey
from crm.media.domain.rules import is_safe_storage_key
from crm.media.domain.value_objects import SignedURL, StoredFile


def build_storage_key(*, organization_id, file_name: str) -> str:
    """organization_id/YYYY/MM/DD/uuid_filename — tenant-prefixed, traversal-safe."""
    now = datetime.now(UTC)
    safe_name = "".join(c for c in (file_name or "file") if c.isalnum() or c in "._-")[:120]
    safe_name = safe_name or "file"
    key = f"{organization_id}/{now:%Y/%m/%d}/{uuid.uuid4().hex}_{safe_name}"
    if not is_safe_storage_key(key):  # pragma: no cover - defensive
        raise UnsafeStorageKey(f"Generated unsafe storage key: {key}")
    return key


def checksum_of(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class BaseStorage(ABC):
    provider: str = ""

    @abstractmethod
    def store_file(self, *, content: bytes, key: str, content_type: str) -> StoredFile: ...

    @abstractmethod
    def open_file(self, storage_key: str) -> bytes: ...

    @abstractmethod
    def delete_file(self, storage_key: str) -> None: ...

    @abstractmethod
    def generate_signed_url(
        self, storage_key: str, *, expires_in: int, asset_id=None
    ) -> SignedURL: ...

    @abstractmethod
    def exists(self, storage_key: str) -> bool: ...

    @staticmethod
    def _guard(storage_key: str) -> None:
        if not is_safe_storage_key(storage_key):
            raise UnsafeStorageKey(f"Refusing to operate on unsafe key: {storage_key!r}")
