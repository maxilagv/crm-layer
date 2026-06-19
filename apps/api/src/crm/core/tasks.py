from celery import shared_task

from crm.core.services.outbox import process_outbox_batch


@shared_task(name="crm.core.tasks.process_outbox", ignore_result=True)
def process_outbox(limit: int = 100) -> int:
    """Periodic task (Celery beat): drain due outbox events."""
    return process_outbox_batch(limit=limit)


@shared_task(name="observability.check_system_health", ignore_result=False)
def check_system_health() -> dict:
    from crm.core.observability.health import SystemStatusBuilder

    return SystemStatusBuilder.build()
