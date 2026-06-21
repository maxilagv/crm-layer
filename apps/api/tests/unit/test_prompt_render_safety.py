"""Guardrail: every prompt placeholder must be provided by the ContextBuilder.

If a prompt references a variable the builder never supplies, rendering fails at
runtime (PromptRenderer raises). This test catches that at edit time for all
seeded prompts, per purpose.
"""

import pytest

from crm.ai.prompts.loader import PROMPT_FOLDERS, load_definition
from crm.ai.prompts.renderer import placeholders_in

# Variables each ContextBuilder.for_* builder provides, per prompt folder.
ALLOWED: dict[str, set[str]] = {
    "sales_agent": {
        "business_name",
        "services_offered",
        "can_quote_prices",
        "price_min",
        "price_max",
        "pricing_policy",
        "commercial_tone",
        "owner_voice",
        "lead_profile",
        "contact_memories",
        "conversation_summary",
        "recent_messages",
        "current_message",
    },
    "support_agent": {
        "business_name",
        "services_offered",
        "support_policy",
        "support_hours",
        "urgent_keywords",
        "owner_voice",
        "client_profile",
        "contact_memories",
        "ticket_context",
        "recent_messages",
        "current_message",
    },
    "assistant_agent": {
        "business_name",
        "services_offered",
        "owner_name",
        "conversation_summary",
        "recent_messages",
        "current_message",
    },
    "lead_scoring": {
        "business_name",
        "services_offered",
        "lead_profile",
        "commercial_history",
        "recent_messages",
    },
    "task_extraction": {
        "business_name",
        "services_offered",
        "current_datetime",
        "timezone",
        "contact_profile",
        "recent_messages",
        "current_message",
    },
    "audio_ticket_extraction": {
        "business_name",
        "services_offered",
        "support_policy",
        "support_hours",
        "urgent_keywords",
        "client_profile",
        "recent_tickets",
        "transcription",
    },
    "conversation_summary": {
        "business_name",
        "services_offered",
        "summary_type",
        "previous_summary",
        "recent_messages",
    },
    "risk_classifier": {
        "business_name",
        "services_offered",
        "context_summary",
        "current_message",
        "proposed_reply",
    },
    "image_generation": {
        "business_name",
        "services_offered",
        "brand_style",
        "image_request",
    },
    "document_draft": {
        "business_name",
        "services_offered",
        "owner_voice",
        "owner_name",
        "doc_type_label",
        "currency",
        "default_tax_rate",
        "default_terms",
        "client_block",
        "today",
        "owner_request",
    },
    "memory_extraction": {
        "business_name",
        "services_offered",
        "contact_name",
        "conversation_summary",
        "existing_memories",
        "recent_messages",
    },
    "project_brief": {
        "business_name",
        "services_offered",
        "owner_voice",
        "owner_name",
        "conversation_summary",
        "recent_messages",
        "deal_value_hint",
    },
    "prospect_qualification": {
        "business_name",
        "services_offered",
        "campaign_vertical",
        "campaign_target_profile",
        "min_fit_score",
        "prospect_profile",
    },
    "outreach_opener": {
        "business_name",
        "services_offered",
        "owner_voice",
        "campaign_vertical",
        "campaign_target_profile",
        "prospect_profile",
        "qualification_signals",
        "recommended_angle",
    },
    "outreach_email": {
        "business_name",
        "services_offered",
        "owner_voice",
        "owner_email",
        "owner_title",
        "campaign_vertical",
        "campaign_target_profile",
        "prospect_profile",
        "qualification_signals",
        "recommended_angle",
        "unsubscribe_line",
    },
    "outreach_reply": {
        "business_name",
        "services_offered",
        "owner_voice",
        "mode",
        "intent",
        "next_action",
        "objection_type",
        "campaign_vertical",
        "campaign_target_profile",
        "prospect_profile",
        "last_outbound",
        "current_message",
        "recent_messages",
    },
    "reply_intent": {
        "business_name",
        "services_offered",
        "prospect_profile",
        "outbound_message",
        "reply_message",
        "recent_messages",
    },
}


@pytest.mark.parametrize("folder", sorted(PROMPT_FOLDERS))
def test_prompt_placeholders_are_provided_by_context(folder):
    definition = load_definition(folder)
    used = (
        placeholders_in(definition.system_prompt)
        | placeholders_in(definition.developer_prompt)
        | placeholders_in(definition.template)
    )
    allowed = ALLOWED[folder]
    unknown = used - allowed
    assert unknown == set(), (
        f"{folder}: prompt usa variables no provistas por el ContextBuilder: {sorted(unknown)}"
    )


@pytest.mark.parametrize("folder", sorted(PROMPT_FOLDERS))
def test_prompt_has_system_and_schema(folder):
    definition = load_definition(folder)
    assert definition.system_prompt.strip(), f"{folder}: system.md vacío"
    # Conversational/structured prompts must ship an output schema.
    assert definition.output_schema is not None, f"{folder}: falta schema.json"
