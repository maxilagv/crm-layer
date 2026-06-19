# Leads

Motor de pipeline comercial del CRM.

## Objetivo

`crm.leads` convierte contactos elegibles en leads, mantiene estado/stage,
calcula score 0-100, guarda snapshots historicos y convierte leads ganados en
clientes.

## Modelos

- `Lead`: estado comercial actual, score, temperatura, señales y resumen.
- `LeadScoreSnapshot`: version historica de cada recalculo de score.
- `LeadStageHistory`: historial append-only de cambios reales de stage.
- `LeadSource`: primer origen comercial del lead.

## Lifecycle

Un contacto `unknown` o `lead` puede convertirse en lead si la conversacion esta
en `sales_ai` o si la creacion manual es explicita. Contactos `client`,
`internal`, `blocked` o con status `blocked` no se convierten automaticamente.

Cada cambio real de stage se registra con `LeadStageHistory`. Cambios repetidos
al mismo stage no crean historial duplicado.

## Scoring

El score final lo calcula backend con factores ponderados:

- `pain_clear`;
- `urgency`;
- `authority`;
- `budget_signal`;
- `business_fit`;
- `engagement`;
- `technical_match`;
- `risk_penalty`.

La IA, cuando se usa, aporta señales estructuradas via
`AIGateway.score_lead()`. El backend ignora el score final propuesto por la IA y
recalcula con sus propios pesos. Si la salida IA es invalida, no se actualiza
`Lead` y no se crea snapshot exitoso.

## Conversion

`convert_to_client()` marca el lead como `won`, mueve el contacto a
`ContactType.CLIENT` y asegura una `SalesOpportunity`.

## Endpoints

- `GET /api/v1/leads/`
- `POST /api/v1/leads/`
- `GET /api/v1/leads/{id}/`
- `PATCH /api/v1/leads/{id}/`
- `POST /api/v1/leads/{id}/score/`
- `POST /api/v1/leads/{id}/convert-to-client/`
- `POST /api/v1/leads/{id}/mark-lost/`
- `POST /api/v1/leads/{id}/schedule-followup/`

## Workers

- `leads.score_lead_from_conversation`
- `leads.detect_hot_lead`

## Integraciones

- AI: solo `AIGateway`, nunca providers directos.
- Audit: eventos relevantes crean `AuditEvent`.
- Outbox: eventos versionados publican cambios comerciales.
- Sales: followups, call requests y opportunities viven en `crm.sales`.

