# `crm.clients` — Client registry & support resolution

Registers **clients** as a first-class concept distinct from leads, and answers
the question that routes every inbound conversation: *is this contact a client
who should go to support?*

## Boundaries

- No AI SDKs, no `crm.ai.providers` imports (clients does not call models).
- Everything is organization-scoped; all mutations are audited.
- A **registered client is never routed to sales** — the conversation router
  sends an active client to `support_ai`.

## Layout

```
domain/      enums, policies, rules, events, value_objects (ClientResolution), exceptions
services/    client_resolver, client_registration, client_lifecycle,
             client_contact, client_service_manager
selectors/   org-scoped read queries
api/         thin views, serializers, permissions, filters, urls
tasks.py     no async work in Phase 7 (documented placeholder)
```

## Models (`clients_*` tables)

| Model | Purpose |
|-------|---------|
| `Client` | A client account: `contact` (PROTECT), optional `company`, `status`, `support_level`, `service_plan`, `onboarding_status`. A **partial unique constraint** guarantees one *active* client per `(organization, contact)`. |
| `ClientContact` | People allowed to act for a client: `role`, `is_primary`, `can_request_support`, `receives_notifications`. Unique per `(organization, client, contact)`. |
| `ClientService` | Contracted services/products for the client. |
| `ClientStatusHistory` | Append-only status transition log. |

## Resolution (`ClientResolver`)

`resolve_by_contact` / `resolve_by_phone` return a `ClientResolution`
value object (`is_client`, `reason`, `client_id`, `support_level`,
`can_request_support`). The reasons are explicit and testable:

- `blocked_contact` → blocked contacts can never request support.
- `active_client_contact` → primary contact of an active client.
- secondary `ClientContact` with `can_request_support=True`.
- `inactive_client` → cancelled/archived clients are **not** auto-routed.

`SUPPORT_ROUTABLE_STATUSES` = active, onboarding, delinquent, paused.

## Registration (`ClientRegistrationService.register`)

Idempotent: reuses the existing `Contact` (a converted lead keeps its contact),
sets `Contact.type = CLIENT`, creates the primary `ClientContact`, writes a
`ClientStatusHistory` row, emits `client.created.v1` and audits. Pass
`raise_on_duplicate=True` (used by the API) to turn a duplicate into a 409.

## Endpoints (`/api/v1/clients/`)

| Method & path | Permission |
|---|---|
| `GET /` (list, filtered) / `POST /` (register) | `clients.view` / `contacts.update` |
| `GET /{id}/` / `PATCH /{id}/` (incl. status change) | `clients.view` / `contacts.update` |
| `GET/POST /{id}/contacts/` | `clients.view` / `contacts.update` |
| `GET/POST /{id}/services/` | `clients.view` / `contacts.update` |

## Tests

`tests/unit/test_clients.py` — registration, unique-active-per-contact,
lead→client contact reuse, **routing to support**, resolver (by contact/phone,
blocked, can_request_support, inactive, org-scoping) and status history.
