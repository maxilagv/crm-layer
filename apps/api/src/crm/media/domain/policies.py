"""Configurable media validation policy (overridable via settings)."""

from django.conf import settings

from .enums import MEDIA_KIND_AUDIO, MEDIA_KIND_DOCUMENT, MEDIA_KIND_IMAGE

_DEFAULT_ALLOWED = {
    MEDIA_KIND_AUDIO: {
        "audio/ogg",
        "audio/mpeg",
        "audio/mp4",
        "audio/wav",
        "audio/webm",
        "audio/x-m4a",
        "audio/amr",
    },
    MEDIA_KIND_IMAGE: {"image/png", "image/jpeg", "image/webp"},
    MEDIA_KIND_DOCUMENT: {
        "application/pdf",
        "text/plain",
        "text/csv",
        # Generated office documents (proposals, quotes, reports, decks).
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
}

# Extensions that must never be accepted regardless of declared MIME.
DANGEROUS_EXTENSIONS = {
    ".exe",
    ".sh",
    ".bat",
    ".cmd",
    ".com",
    ".js",
    ".jar",
    ".php",
    ".py",
    ".rb",
    ".pl",
    ".dll",
    ".so",
    ".bin",
    ".msi",
    ".scr",
    ".ps1",
}

# 25 MB default cap (WhatsApp media is well under this).
_DEFAULT_MAX_BYTES = 25 * 1024 * 1024


def allowed_mime_types() -> set[str]:
    override = getattr(settings, "MEDIA_ALLOWED_MIME_TYPES", None)
    if override:
        return set(override)
    return {mime for kinds in _DEFAULT_ALLOWED.values() for mime in kinds}


def allowed_audio_mime_types() -> set[str]:
    return set(_DEFAULT_ALLOWED[MEDIA_KIND_AUDIO])


def allowed_image_mime_types() -> set[str]:
    return set(_DEFAULT_ALLOWED[MEDIA_KIND_IMAGE])


def max_size_bytes() -> int:
    return int(getattr(settings, "MEDIA_MAX_SIZE_BYTES", _DEFAULT_MAX_BYTES))


def kind_for_mime(mime_type: str) -> str | None:
    for kind, mimes in _DEFAULT_ALLOWED.items():
        if mime_type in mimes:
            return kind
    if (mime_type or "").startswith("audio/"):
        return MEDIA_KIND_AUDIO
    if (mime_type or "").startswith("image/"):
        return MEDIA_KIND_IMAGE
    return None


def signed_url_ttl_seconds() -> int:
    return int(getattr(settings, "MEDIA_SIGNED_URL_TTL_SECONDS", 300))
