from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from crm.core.logging import sanitize

SENSITIVE_QUERY_PARTS = (
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "code",
    "password",
    "secret",
    "signature",
    "token",
)


def sanitize_payload(value: Any) -> Any:
    return sanitize(value)


def sanitize_error_message(message: str, *, limit: int = 1000) -> str:
    clean = str(sanitize({"message": message}).get("message", ""))
    return clean[:limit]


def sanitize_url(raw_url: str) -> tuple[str, str, str]:
    """Return sanitized host, path+safe-query and a stable hash of the original URL."""
    if not raw_url:
        return "", "", ""
    parsed = urlsplit(raw_url)
    safe_query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if any(part in lowered for part in SENSITIVE_QUERY_PARTS):
            safe_query.append((key, "[REDACTED]"))
        else:
            safe_query.append((key, value))
    path = urlunsplit(("", "", parsed.path, urlencode(safe_query), ""))
    return parsed.netloc[:255], path[:512], hashlib.sha256(raw_url.encode()).hexdigest()
