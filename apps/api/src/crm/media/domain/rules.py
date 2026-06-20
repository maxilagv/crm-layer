"""Pure media rules (no I/O)."""

import re

# Reject storage keys that could escape the tenant prefix.
_UNSAFE_KEY = re.compile(r"(^/|\.\.|//|\\|\0)")


def is_safe_storage_key(storage_key: str) -> bool:
    if not storage_key or storage_key.strip() != storage_key:
        return False
    return _UNSAFE_KEY.search(storage_key) is None


def is_audio_mime(mime_type: str) -> bool:
    return (mime_type or "").startswith("audio/")
