"""Structured output schemas (Pydantic v2). Importing this package registers all."""

from .assistant_reply import AssistantReplySchema
from .audio_transcription import AudioTranscriptionSchema
from .base import (
    AISchema,
    example_output_for_purpose,
    json_schema_for_purpose,
    register_schema,
    schema_for_purpose,
)
from .conversation_summary import ConversationSummarySchema
from .document_draft import DocumentDraftSchema
from .embedding import EmbeddingSchema
from .image_generation import ImageGenerationSchema
from .lead_score import LeadScoreSchema
from .memory_extraction import MemoryExtractionSchema
from .moderation_result import ModerationResultSchema
from .outreach_email import OutreachEmailSchema
from .outreach_opener import OutreachOpenerSchema
from .outreach_reply import OutreachReplySchema
from .project_brief import ProjectBriefSchema
from .prospect_qualification import ProspectQualificationSchema
from .reply_intent import ReplyIntentSchema
from .sales_reply import SalesReplySchema
from .support_reply import SupportReplySchema
from .support_ticket import SupportTicketSchema
from .task_candidate import TaskCandidateSchema, TaskExtractionSchema

__all__ = [
    "AISchema",
    "AssistantReplySchema",
    "AudioTranscriptionSchema",
    "ConversationSummarySchema",
    "DocumentDraftSchema",
    "EmbeddingSchema",
    "ImageGenerationSchema",
    "LeadScoreSchema",
    "MemoryExtractionSchema",
    "ModerationResultSchema",
    "OutreachEmailSchema",
    "OutreachOpenerSchema",
    "OutreachReplySchema",
    "ProjectBriefSchema",
    "ProspectQualificationSchema",
    "ReplyIntentSchema",
    "SalesReplySchema",
    "SupportReplySchema",
    "SupportTicketSchema",
    "TaskCandidateSchema",
    "TaskExtractionSchema",
    "example_output_for_purpose",
    "json_schema_for_purpose",
    "register_schema",
    "schema_for_purpose",
]
