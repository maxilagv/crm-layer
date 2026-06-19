from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)

SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(access_token|api_key|apikey|authorization|password|secret|token)=([^\s&]+)"
)


def is_sensitive_key(key: Any) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if is_sensitive_key(key) else sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize(item) for item in value)
    if isinstance(value, str):
        return SECRET_ASSIGNMENT_RE.sub(r"\1=[REDACTED]", value)
    return value
