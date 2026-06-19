from __future__ import annotations

import logging

from celery import signals

from .context import clear_request_context, get_context, set_request_context
from .metrics import MetricsRecorder

logger = logging.getLogger(__name__)


@signals.before_task_publish.connect
def inject_context(headers=None, **_kwargs):
    if headers is None:
        return
    headers["observability_context"] = {key: value for key, value in get_context().items() if value}


@signals.task_prerun.connect
def restore_context(task=None, **_kwargs):
    request = getattr(task, "request", None)
    headers = getattr(request, "headers", None) or {}
    context = headers.get("observability_context") or {}
    request_id = context.get("request_id")
    correlation_id = context.get("correlation_id") or request_id
    if request_id:
        set_request_context(
            request_id=request_id,
            correlation_id=correlation_id,
            organization_id=context.get("organization_id"),
            user_id=context.get("user_id"),
        )
    MetricsRecorder.increment("celery_tasks_total", task=getattr(task, "name", "unknown"))


@signals.task_failure.connect
def record_task_failure(task_id=None, exception=None, sender=None, **_kwargs):
    task_name = getattr(sender, "name", "unknown")
    MetricsRecorder.increment("celery_task_failures_total", task=task_name)
    logger.warning(
        "Celery task failed",
        extra={
            "event": "celery.task_failed",
            "metadata": {
                "task_id": task_id,
                "task": task_name,
                "error": str(exception)[:1000],
            },
        },
    )


@signals.task_postrun.connect
def clear_context(**_kwargs):
    clear_request_context()
