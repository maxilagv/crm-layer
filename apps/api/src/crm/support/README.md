# `crm.support` — Tickets, triage, support replies

Turns client messages and audios into triaged **support tickets**, manages their
lifecycle, drafts safe replies and notifies the owner on urgent/critical issues.

## Boundaries (non-negotiable)

- **AI only via `AIGateway`.** Ticket extraction from audio, support-reply drafts
  and any model call go through `crm.ai.services.ai_gateway.AIGateway`. No
  `openai`/`anthropic` imports, no `crm.ai.providers` imports.
- **The backend owns classification.** Deterministic triage runs first; AI may
  only *raise* priority or fill a missing category — never lower the backend's
  decision.
- **AI tickets come only from validated structured output.** Free text is never
  parsed to mutate data; `create_from_ai_extraction` consumes a schema-validated
  dict produced by the gateway. Invalid output ⇒ no ticket.
- **Critical tickets are never resolved by AI alone** (`CriticalTicketAIResolveDenied`).
- **Support never asks for passwords or tokens** — enforced by `SafetyGuard` on
  every generated reply via the gateway.
- Dedupe by `source_message_id` (partial unique), idempotent owner notification,
  internal comments are never sent to the client.

## Layout

```
domain/      enums, policies (keywords, elevating levels), rules (normalize, ai_may_resolve), events, exceptions
services/    ticket_triage, ticket_creator, ticket_lifecycle, urgent_ticket_notifier,
             known_issue_matcher, ticket_from_audio, support_reply,
             support_policy (SupportPolicyAdapter), owner_whatsapp_adapter
selectors/   org-scoped read queries
api/         thin views, serializers, permissions (tickets.manage), filters, urls
tasks.py     Celery workers (idempotent, retry-safe)
```

## Models (`support_*` tables)

| Model | Purpose |
|-------|---------|
| `SupportTicket` | `client` (SET_NULL), `contact` (PROTECT), `conversation_id`, `source_message_id` (partial-unique), `status`, `priority`, `category`, summaries, `assigned_user`. |
| `SupportTicketEvent` | Append-only audit trail of every transition/comment/attachment. |
| `SupportTicketComment` | `visibility` = internal/public; internal stays internal. |
| `SupportTicketAttachment` | Links a `MediaAsset` (PROTECT) — e.g. the source audio. |
| `SupportKnownIssue` | Operator-curated known issues matched by keyword (suggested, never auto-applied). |
| `SupportResolution` | Resolution record incl. `resolved_by_type` and `ai_run_id`. |

## Triage (`SupportTriageService.triage`)

Deterministic category (keyword map: access/billing/integration/performance/…),
deterministic priority (urgent/critical keywords + org-configured keywords), VIP
/priority **support-level elevation**, `missing_information ⇒ waiting_client`, and
finally an AI hint that can only raise priority. Returns a `TriageResult` with
`requires_owner_notification`.

## Lifecycle (`TicketLifecycleService`)

`assign` (open→in_progress), `change_status`, `resolve` (guards critical+AI),
`reopen`, `close`, `add_comment`, `add_attachment`. Every mutation records an
event + audit entry and emits an outbox event.

## Audio → ticket (`TicketFromAudioService`)

`MediaAsset` → `AudioTranscriptionService.transcribe` (gateway) →
`AIGateway.extract_ticket_from_audio` (structured) →
`SupportTicketCreator.create_from_ai_extraction` → attach the source audio.

## Endpoints (`/api/v1/…`, all `tickets.manage`)

`GET/POST tickets/`, `GET/PATCH tickets/{id}/`,
`POST tickets/{id}/{assign,resolve,reopen}/`,
`POST tickets/{id}/{comments,attachments}/`,
`GET/POST support/known-issues/`, `GET/PATCH support/known-issues/{id}/`.

## Workers (`crm.support.tasks`)

`support.create_ticket_from_audio`, `support.triage_ticket`,
`support.generate_support_reply`, `support.notify_owner_for_urgent_ticket` —
idempotent and retry-safe.

## Tests

`tests/unit/test_support.py` (triage rules, creation, dedupe, lifecycle,
critical-AI-resolve denial, comments, known issues) and
`tests/unit/test_phase7_pipeline.py` (audio→ticket, invalid-output→no-ticket,
password-request blocked, safe reply) plus the API and anti-coupling suites.
