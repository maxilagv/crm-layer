# Fase 3 — Implementación (CRM core: contactos, conversaciones, mensajes)

Resumen de lo construido sobre la base de Fase 1 (core/outbox/envelope) y Fase 2
(auth, organizaciones, permisos, audit). Esta fase **no** llama WhatsApp ni IA
reales: `send-message` es un envío simulado (persiste mensaje + evento).

## Apps y estructura

- `crm.contacts`: `constants.py`, `normalizers.py`, `models.py`, `selectors.py`,
  `services.py`, `permissions.py`, `exceptions.py`, `api/{serializers,views,urls}.py`.
- `crm.conversations`: `constants.py`, `normalizers.py`, `router.py`, `models.py`,
  `selectors.py`, `services.py`, `permissions.py`, `api/{serializers,views,urls}.py`.

Convención (igual que Fase 2): views delgadas (`APIView`), mutaciones en services,
lecturas en selectors, choices centralizados en `constants.py`. `organization_id`
es UUID (de `BaseModel`), no FK; las relaciones que el inbox embebe (contact,
assigned_user, conversation) sí son FKs para `select_related` sin N+1.

## Modelos

contacts: `Contact`, `ContactPhone`, `ContactEmail`, `Company`, `ContactCompany`,
`ContactTag`, `ContactNote`, `ContactEvent`.
conversations: `Conversation`, `Message`, `MessageAttachment`,
`ConversationSummary`, `ConversationMemory`.

`on_delete`: phones/emails/notes/tags/company_links/attachments/messages → CASCADE;
`Conversation.contact` y `Message.contact` → PROTECT (preservar historial);
`assigned_user`/`note.author` → SET_NULL. Borrado operativo = soft delete (`deleted_at`).

## Normalización telefónica (E.164)

`contacts/normalizers.py` usa `phonenumbers`. `normalize_phone(raw, region=None)`
acepta `+54…`, `11 1234-5678`, `(011) 1234-5678` y devuelve E.164 canónico +
`country_code` + región; lanza `PhoneNormalizationError` si es inválido/ambiguo.
Región por defecto: `settings.CONTACTS_DEFAULT_PHONE_REGION` (default `"AR"`).
`phone_e164` es la fuente de verdad; el input crudo solo va a `metadata` si se pasa.

## Deduplicación de contactos

Por teléfono, nunca por nombre. Constraint único `(organization_id, phone_e164)`
en `ContactPhone`; emails secundarios con único `(organization_id, normalized_email)`.
`ContactResolver.resolve_by_phone` normaliza, busca y crea atómicamente
(`transaction.atomic` + recuperación por `IntegrityError` ante carreras), devolviendo
`{contact, created, matched_by, phone}`. El mismo número puede existir en otra
organización (multi-tenant).

## Resolución de conversaciones

`ConversationResolver.resolve(org, contact, channel)` reutiliza una conversación
`open`/`pending` para `(contact, channel)`; si no hay, crea una con `mode` calculado
por `ConversationRouter` y emite `conversation.created.v1`.

## ConversationRouter (puro y testeable, `router.py`)

Orden: 1) contacto blocked → `blocked`; 2) conversación closed/archived → mantiene
mode; 3) `mode == paused` → `paused`; 4) `ai_enabled == False` → `manual`;
5) client → `support_ai`; 6) lead → `sales_ai`; 7) internal → `internal_assistant`;
8) fallback → `manual`. `resume-ai` levanta el pause **antes** de rerutear (en
`ConversationHandoffService`), así el router queda puro.

## Eventos internos (outbox de Fase 1)

`contact.created.v1`, `contact.updated.v1`, `conversation.created.v1`,
`conversation.mode_changed.v1`, `conversation.message_received.v1`,
`conversation.message_sent.v1`, `conversation.handoff_requested.v1`. Se crean en la
**misma** `transaction.atomic` que el cambio de negocio (probado con un test de
rollback). Payload versionado: `{event_type, organization_id, data{…ids}, metadata{request_id}}`.
Sin tokens/secretos/raw_payload. Las acciones humanas además quedan en `audit`.

## Permisos (Fase 2)

`contacts.view/create/update`, `conversations.view/reply/takeover` vía
`RequiresPermission`. Colecciones/detalle eligen permiso por método; notas/tags/merge
requieren `contacts.update`; acciones de conversación requieren `conversations.takeover`;
`send-message` requiere `conversations.reply`.

## Endpoints (`/api/v1/`)

contacts: `GET/POST /contacts/`, `GET/PATCH/DELETE /contacts/{id}/`,
`POST /contacts/{id}/notes/`, `POST /contacts/{id}/tags/`, `POST /contacts/merge/`.
conversations: `GET /conversations/`, `GET /conversations/{id}/`,
`GET /conversations/{id}/messages/`, `POST /conversations/{id}/send-message/`,
`POST .../takeover|pause-ai|resume-ai|close|reopen/`.

Inbox (`GET /conversations/`): orden por `last_message_at` desc; contacto +
assigned_user via `select_related`; preview del último mensaje via subqueries
anotadas; teléfono primario via `Prefetch` → sin N+1 (test `test_inbox_has_no_n_plus_one`).
`raw_payload` y `metadata` de mensajes nunca se exponen.

## Tests

57 tests de Fase 3 (normalización, dedup, resolver, merge, router matrix,
ingestión + dedup por `external_message_id`, timestamps, pause/resume/takeover/
close/reopen, eventos en transacción, aislamiento multi-tenant, permisos, N+1,
raw_payload oculto). Más OpenAPI en el schema. Ningún test llama proveedores reales.

## Nota de entorno (test database)

La app `crm.whatsapp` (en desarrollo en paralelo) introdujo un período sin
migraciones; mientras eso ocurra, `migrate --run-syncdb` (que usa la creación de la
test DB) falla por orden de FKs hacia `conversations_conversation`. Una vez que
`whatsapp` tiene su migración inicial, `python manage.py migrate` y la creación normal
de la test DB funcionan. Para correr solo Fase 3 de forma aislada:
`pytest tests/unit/test_contacts.py tests/unit/test_conversations.py
tests/unit/test_conversation_router.py tests/api/test_contacts_api.py
tests/api/test_conversations_api.py`.
