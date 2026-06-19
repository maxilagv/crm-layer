# document_draft

Drafts a complete, professional document payload (proposal / quote / report /
deck) from a short free-text request by the owner. The validated output matches
`crm.documents.domain.payload.normalize_payload()` and is passed straight to
`DocumentService.generate(payload=...)`.

- **Purpose:** `AIPurpose.DOCUMENT_DRAFT`
- **Schema:** `crm.ai.schemas.document_draft.DocumentDraftSchema`
- **Variables:** `business_name`, `services_offered`, `owner_name`, `doc_type_label`,
  `currency`, `default_tax_rate`, `default_terms`, `client_block`, `today`, `owner_request`
  (provided by `ContextBuilder.for_document_draft`).
- **Gemini-friendly:** runs in `generate_structured` (json_object); no tool-calling,
  no SafetyGuard (owner-only, internal draft).
