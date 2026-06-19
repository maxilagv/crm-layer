"""Structured JSON logging with basic secret redaction."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from .observability.sanitization import sanitize as sanitize_value
from .request_context import (
    correlation_id_var,
    organization_id_var,
    request_id_var,
    user_id_var,
)

# Any dict key containing one of these substrings gets its value redacted.
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


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def sanitize(value: Any) -> Any:
    return sanitize_value(value)


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, dict):
            record.args = sanitize(record.args)
        metadata = getattr(record, "metadata", None)
        if isinstance(metadata, dict):
            record.metadata = sanitize(metadata)
        return True


class JSONFormatter(logging.Formatter):
    def __init__(self, *, environment: str, service: str) -> None:
        super().__init__()
        self.environment = environment
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "environment": self.environment,
            "service": self.service,
            "request_id": getattr(record, "request_id", None) or request_id_var.get(),
            "correlation_id": getattr(record, "correlation_id", None) or correlation_id_var.get(),
            "organization_id": getattr(record, "organization_id", None)
            or organization_id_var.get(),
            "user_id": getattr(record, "user_id", None) or user_id_var.get(),
            "event": getattr(record, "event", record.name),
            "message": record.getMessage(),
            "metadata": sanitize(getattr(record, "metadata", {})),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=True)
