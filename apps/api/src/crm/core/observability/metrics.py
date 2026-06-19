from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from threading import Lock


class MetricsRecorder:
    """Small process-local recorder used for tests, logs and health summaries.

    Durable business metrics live in analytics snapshots. This recorder is for
    low-latency technical counters when no Prometheus backend is configured yet.
    """

    _lock = Lock()
    _counters: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    _gauges: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    @classmethod
    def increment(cls, name: str, value=1, **labels) -> Decimal:
        key = _metric_key(name, labels)
        with cls._lock:
            cls._counters[key] += Decimal(str(value))
            return cls._counters[key]

    @classmethod
    def gauge(cls, name: str, value, **labels) -> Decimal:
        key = _metric_key(name, labels)
        with cls._lock:
            cls._gauges[key] = Decimal(str(value))
            return cls._gauges[key]

    @classmethod
    def snapshot(cls) -> dict:
        with cls._lock:
            return {
                "counters": {key: str(value) for key, value in cls._counters.items()},
                "gauges": {key: str(value) for key, value in cls._gauges.items()},
            }

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._counters.clear()
            cls._gauges.clear()


def _metric_key(name: str, labels: dict) -> str:
    if not labels:
        return name
    label_text = ",".join(f"{key}={labels[key]}" for key in sorted(labels))
    return f"{name}|{label_text}"
