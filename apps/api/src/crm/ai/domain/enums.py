"""Centralized enums for the AI platform. No scattered strings."""

from django.db import models


class AIProviderType(models.TextChoices):
    OPENAI = "openai", "OpenAI"
    ANTHROPIC = "anthropic", "Anthropic"
    GEMINI = "gemini", "Google Gemini"
    FAKE = "fake", "Fake"


class AIPurpose(models.TextChoices):
    SALES_REPLY = "sales_reply", "Sales reply"
    SUPPORT_REPLY = "support_reply", "Support reply"
    LEAD_SCORING = "lead_scoring", "Lead scoring"
    TASK_EXTRACTION = "task_extraction", "Task extraction"
    AUDIO_TRANSCRIPTION = "audio_transcription", "Audio transcription"
    CONVERSATION_SUMMARY = "conversation_summary", "Conversation summary"
    IMAGE_GENERATION = "image_generation", "Image generation"
    EMBEDDING = "embedding", "Embedding"
    RISK_CLASSIFICATION = "risk_classification", "Risk classification"
    AUDIO_TICKET_EXTRACTION = "audio_ticket_extraction", "Audio ticket extraction"
    ASSISTANT_REPLY = "assistant_reply", "Assistant reply"
    DOCUMENT_DRAFT = "document_draft", "Document draft"
    MEMORY_EXTRACTION = "memory_extraction", "Memory extraction"
    PROJECT_BRIEF = "project_brief", "Project brief"
    PROSPECT_QUALIFICATION = "prospect_qualification", "Prospect qualification"
    OUTREACH_OPENER = "outreach_opener", "Outreach opener"
    OUTREACH_REPLY = "outreach_reply", "Outreach reply"
    REPLY_INTENT = "reply_intent", "Reply intent"


class AIRunStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"
    FALLBACK_USED = "fallback_used", "Fallback used"
    SCHEMA_INVALID = "schema_invalid", "Schema invalid"
    BLOCKED_BY_SAFETY = "blocked_by_safety", "Blocked by safety"


class PromptStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class ToolCallStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    APPROVED = "approved", "Approved"
    EXECUTED = "executed", "Executed"
    BLOCKED = "blocked", "Blocked"
    FAILED = "failed", "Failed"
    SKIPPED = "skipped", "Skipped"
    DUPLICATE = "duplicate", "Duplicate"


class SafetyDecision(models.TextChoices):
    SEND = "send", "Send"
    REVISE = "revise", "Revise"
    ASK_CLARIFYING_QUESTION = "ask_clarifying_question", "Ask clarifying question"
    HANDOFF_TO_HUMAN = "handoff_to_human", "Handoff to human"
    DO_NOT_REPLY = "do_not_reply", "Do not reply"
    NOTIFY_OWNER = "notify_owner", "Notify owner"


class RiskLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class ModelCapability(models.TextChoices):
    TOOLS = "tools", "Tool calling"
    STRUCTURED_OUTPUTS = "structured_outputs", "Structured outputs"
    AUDIO = "audio", "Audio"
    IMAGES = "images", "Images"
    EMBEDDINGS = "embeddings", "Embeddings"


class AIMessageRole(models.TextChoices):
    SYSTEM = "system", "System"
    DEVELOPER = "developer", "Developer"
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"
    TOOL = "tool", "Tool"


# Purposes whose outputs mutate business data and therefore REQUIRE a schema.
PURPOSES_REQUIRING_SCHEMA = frozenset(
    {
        AIPurpose.SALES_REPLY,
        AIPurpose.SUPPORT_REPLY,
        AIPurpose.LEAD_SCORING,
        AIPurpose.TASK_EXTRACTION,
        AIPurpose.AUDIO_TICKET_EXTRACTION,
        AIPurpose.RISK_CLASSIFICATION,
        AIPurpose.ASSISTANT_REPLY,
        AIPurpose.DOCUMENT_DRAFT,
        AIPurpose.MEMORY_EXTRACTION,
        AIPurpose.PROJECT_BRIEF,
        AIPurpose.PROSPECT_QUALIFICATION,
        AIPurpose.OUTREACH_OPENER,
        AIPurpose.OUTREACH_REPLY,
        AIPurpose.REPLY_INTENT,
    }
)

RISK_ORDER = {
    RiskLevel.LOW.value: 0,
    RiskLevel.MEDIUM.value: 1,
    RiskLevel.HIGH.value: 2,
    RiskLevel.CRITICAL.value: 3,
}


def max_risk(*levels: str) -> str:
    """Return the highest of the given risk levels."""
    present = [level for level in levels if level in RISK_ORDER]
    if not present:
        return RiskLevel.LOW.value
    return max(present, key=lambda level: RISK_ORDER[level])
