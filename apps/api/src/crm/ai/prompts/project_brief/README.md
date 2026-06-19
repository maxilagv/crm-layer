# project_brief

Turns a conversation with a prospect/client into a development-ready project
brief (Phase 9.4): objectives, scope, deliverables, milestones, open questions,
estimates and next steps.

- **Purpose:** `AIPurpose.PROJECT_BRIEF`
- **Schema:** `crm.ai.schemas.project_brief.ProjectBriefSchema`
- **Variables:** `business_name`, `owner_name`, `owner_voice`, `conversation_summary`,
  `recent_messages`, `deal_value_hint` (from `ContextBuilder.for_project_brief`).
- Owner-only / internal; Gemini-friendly (`generate_structured`); no SafetyGuard.
