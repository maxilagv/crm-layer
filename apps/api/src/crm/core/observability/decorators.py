from __future__ import annotations

from functools import wraps

from .metrics import MetricsRecorder


def counted(metric_name: str, **labels):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            MetricsRecorder.increment(metric_name, **labels)
            return func(*args, **kwargs)

        return wrapper

    return decorator
