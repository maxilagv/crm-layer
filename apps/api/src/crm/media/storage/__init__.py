"""Private storage adapters + signed URL helpers."""

from .base import BaseStorage
from .local_storage import LocalPrivateStorage
from .s3_storage import S3PrivateStorage


def get_storage(provider: str | None = None) -> BaseStorage:
    """Resolve the active storage backend.

    Defaults to S3 only when ``MEDIA_STORAGE_PROVIDER=s3`` and S3 is configured;
    otherwise LocalPrivateStorage (used in tests and local dev).
    """
    from django.conf import settings

    provider = provider or getattr(settings, "MEDIA_STORAGE_PROVIDER", "local")
    if provider == "s3" and getattr(settings, "S3_BUCKET_NAME", ""):
        return S3PrivateStorage()
    return LocalPrivateStorage()


__all__ = ["BaseStorage", "LocalPrivateStorage", "S3PrivateStorage", "get_storage"]
