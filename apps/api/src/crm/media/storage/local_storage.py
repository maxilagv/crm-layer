"""Local private storage: files under a non-public root, served via signed token.

The signed URL points at the internal protected download endpoint with a
time-limited token; the storage path is never exposed.
"""

from pathlib import Path

from django.conf import settings
from django.urls import reverse

from crm.media.domain.exceptions import MediaError
from crm.media.domain.policies import signed_url_ttl_seconds
from crm.media.domain.value_objects import SignedURL, StoredFile

from .base import BaseStorage, checksum_of
from .signed_urls import sign_asset


def _root() -> Path:
    configured = getattr(settings, "MEDIA_PRIVATE_ROOT", None)
    base = Path(configured) if configured else Path(settings.BASE_DIR) / "private_media"
    return base


class LocalPrivateStorage(BaseStorage):
    provider = "local"

    def _path(self, storage_key: str) -> Path:
        self._guard(storage_key)
        full = (_root() / storage_key).resolve()
        root = _root().resolve()
        # Defense in depth: the resolved path must stay within the root.
        if root not in full.parents and full != root:
            raise MediaError("Resolved path escapes the private media root")
        return full

    def store_file(self, *, content: bytes, key: str, content_type: str) -> StoredFile:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return StoredFile(
            storage_key=key,
            storage_provider=self.provider,
            size_bytes=len(content),
            checksum=checksum_of(content),
        )

    def open_file(self, storage_key: str) -> bytes:
        return self._path(storage_key).read_bytes()

    def delete_file(self, storage_key: str) -> None:
        path = self._path(storage_key)
        if path.exists():
            path.unlink()

    def exists(self, storage_key: str) -> bool:
        return self._path(storage_key).exists()

    def generate_signed_url(self, storage_key: str, *, expires_in: int, asset_id=None) -> SignedURL:
        if asset_id is None:
            raise MediaError("Local signed URLs require an asset id")
        ttl = expires_in or signed_url_ttl_seconds()
        token = sign_asset(asset_id)
        path = reverse("media-internal-download")
        return SignedURL(url=f"{path}?token={token}", expires_in=ttl)
