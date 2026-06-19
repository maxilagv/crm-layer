from django.utils.dateparse import parse_datetime

from crm.ai.services.ai_gateway import AIGateway
from crm.tasks.domain.enums import TaskPriority
from crm.tasks.domain.value_objects import TaskCandidate, TaskExtractionResult

from .task_creator import TaskCreator

MIN_CONFIDENCE = 0.65


class TaskExtractor:
    @staticmethod
    def extract_from_message(
        *, organization, conversation, message, actor=None, metadata=None, auto_confirm=False
    ):
        """Extract tasks from a message and persist the confident ones.

        ``auto_confirm=True`` bypasses the per-candidate ``requires_confirmation`` guard
        (used when the owner explicitly dictates a task via the personal assistant), so a
        clear "recordame X" lands directly as a card. Confidence is still required.
        """
        result = AIGateway.extract_tasks(
            conversation_id=conversation.id,
            message_id=message.id,
            actor=actor,
            metadata=metadata or {},
        )
        if not result.succeeded or not result.data:
            return TaskExtractionResult(
                created_count=0,
                skipped_count=0,
                tasks=[],
                ai_run_id=result.run_id,
                reason=result.error_code or "ai_task_extraction_failed",
            )

        created_tasks = []
        skipped = 0
        for raw in result.data.get("tasks") or []:
            candidate = _candidate_from_ai(raw, ai_run_id=result.run_id)
            if (
                candidate is None
                or candidate.confidence < MIN_CONFIDENCE
                or (candidate.requires_confirmation and not auto_confirm)
            ):
                skipped += 1
                continue
            task, created = TaskCreator.create_from_candidate(
                organization=organization,
                candidate=candidate,
                conversation=conversation,
                message=message,
                actor=actor,
            )
            if created:
                created_tasks.append(task)
            else:
                skipped += 1
        return TaskExtractionResult(
            created_count=len(created_tasks),
            skipped_count=skipped,
            tasks=created_tasks,
            ai_run_id=result.run_id,
        )


def _candidate_from_ai(raw: dict, *, ai_run_id):
    title = str(raw.get("title") or "").strip()
    if not title:
        return None
    due_at = parse_datetime(raw["due_at"]) if raw.get("due_at") else None
    priority = str(raw.get("priority") or TaskPriority.MEDIUM.value)
    if priority not in TaskPriority.values:
        priority = TaskPriority.MEDIUM.value
    return TaskCandidate(
        title=title,
        description=str(raw.get("description") or ""),
        due_at=due_at,
        priority=priority,
        confidence=float(raw.get("confidence") or 0),
        requires_confirmation=bool(raw.get("requires_confirmation", True)),
        ai_run_id=ai_run_id,
        metadata={"raw_candidate": {k: v for k, v in raw.items() if k != "raw_payload"}},
    )
