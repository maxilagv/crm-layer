"""MIME / size / checksum / extension / path validation for media."""

from pathlib import PurePosixPath

from crm.media.domain import policies
from crm.media.domain.exceptions import (
    EmptyMediaFile,
    MediaTooLarge,
    MediaValidationError,
    UnsupportedMediaType,
)
from crm.media.domain.value_objects import ValidatedMedia

from .base import checksum_of


def validate_media(
    *,
    content: bytes,
    mime_type: str,
    file_name: str,
    require_known_mime: bool = True,
) -> ValidatedMedia:
    if content is None or len(content) == 0:
        raise EmptyMediaFile()

    size = len(content)
    if size > policies.max_size_bytes():
        raise MediaTooLarge(f"File exceeds {policies.max_size_bytes()} bytes")

    extension = PurePosixPath(file_name or "").suffix.lower()
    if extension in policies.DANGEROUS_EXTENSIONS:
        raise UnsupportedMediaType(f"Extension '{extension}' is not allowed")

    kind = policies.kind_for_mime(mime_type)
    if mime_type not in policies.allowed_mime_types():
        if require_known_mime or kind is None:
            raise UnsupportedMediaType(f"MIME type '{mime_type}' is not allowed")

    if kind is None:
        raise MediaValidationError(f"Could not classify MIME type '{mime_type}'")

    return ValidatedMedia(
        mime_type=mime_type,
        size_bytes=size,
        checksum=checksum_of(content),
        kind=kind,
    )
