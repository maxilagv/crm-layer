"""Versioned internal event types emitted by the AI module via the outbox."""

EVENT_AI_RUN_COMPLETED = "ai.run_completed.v1"
EVENT_AI_RUN_FAILED = "ai.run_failed.v1"
EVENT_AI_REPLY_BLOCKED = "ai.reply_blocked.v1"
EVENT_AI_HANDOFF_REQUESTED = "ai.handoff_requested.v1"
EVENT_AI_OWNER_NOTIFICATION = "ai.owner_notification_requested.v1"
EVENT_AI_TASK_CANDIDATE = "ai.task_candidate_created.v1"
EVENT_AI_CALL_REQUESTED = "ai.call_request_created.v1"
