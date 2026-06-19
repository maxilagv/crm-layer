from celery import shared_task


@shared_task(name="audit.compact_old_logs", ignore_result=False)
def compact_old_logs(*, days: int | None = None):
    from crm.audit.services import AuditRetentionService

    return AuditRetentionService.compact_old_logs(days=days)
