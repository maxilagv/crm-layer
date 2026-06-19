from crm.tasks.domain.rules import normalize_title
from crm.tasks.models import Task, TaskSource


class TaskDeduplicationService:
    @staticmethod
    def find_duplicate(
        *,
        organization_id,
        title: str,
        source_message=None,
        idempotency_key: str = "",
    ) -> Task | None:
        if idempotency_key:
            existing = Task.objects.filter(
                organization_id=organization_id, idempotency_key=idempotency_key
            ).first()
            if existing is not None:
                return existing
        if source_message is None:
            return None
        normalized = normalize_title(title)
        source = (
            TaskSource.objects.filter(
                organization_id=organization_id,
                source_message=source_message,
                normalized_title=normalized,
            )
            .select_related("task")
            .first()
        )
        return source.task if source is not None else None
