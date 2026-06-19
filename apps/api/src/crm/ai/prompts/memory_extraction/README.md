# memory_extraction

Extracts durable, typed memory facts about a contact from a conversation
(Phase 9.1). The validated output is persisted as `ConversationMemory` rows via
`ConversationMemoryService.persist_extracted_facts` and later injected back into
sales/support replies by `ContextBuilder._contact_memories`.

- **Purpose:** `AIPurpose.MEMORY_EXTRACTION`
- **Schema:** `crm.ai.schemas.memory_extraction.MemoryExtractionSchema`
- **Variables:** `business_name`, `contact_name`, `conversation_summary`,
  `existing_memories`, `recent_messages` (from `ContextBuilder.for_memory_extraction`).
- Gemini-friendly (`generate_structured` / json_object); no SafetyGuard.
