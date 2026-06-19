from __future__ import annotations

import logging

from .context import get_context
from .sanitization import sanitize


def log_event(logger: logging.Logger, level: int, event: str, message: str, **metadata) -> None:
    context = {key: value for key, value in get_context().items() if value}
    logger.log(
        level,
        message,
        extra={
            "event": event,
            **context,
            "metadata": sanitize(metadata),
        },
    )
