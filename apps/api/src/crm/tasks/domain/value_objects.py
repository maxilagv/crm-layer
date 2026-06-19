from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class TaskCandidate:
    title: str
    description: str = ""
    due_at: datetime | None = None
    priority: str = "medium"
    confidence: float = 0
    requires_confirmation: bool = True
    source_message_id: UUID | None = None
    ai_run_id: UUID | None = None
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TaskExtractionResult:
    created_count: int
    skipped_count: int
    tasks: list
    ai_run_id: UUID | None = None
    reason: str = ""
