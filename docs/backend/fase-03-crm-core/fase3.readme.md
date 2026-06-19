# Fase 3: CRM core, contactos, conversaciones y mensajes

## Objetivo

Crear la base operativa del CRM: contactos, empresas, telefonos, conversaciones, mensajes, participantes, resumenes y estado conversacional.

Esta fase todavia no necesita WhatsApp real ni IA real. Puede trabajar con datos manuales o simulados. Pero debe dejar lista la estructura donde despues entraran los mensajes de WhatsApp.

## Resultado esperado

Al terminar esta fase el backend debe poder:

- crear y editar contactos;
- normalizar telefonos;
- deduplicar por telefono;
- modelar empresas;
- abrir conversaciones;
- guardar mensajes;
- asociar attachments;
- pausar o reactivar IA en una conversacion;
- tomar control manual;
- generar eventos internos de contacto/conversacion/mensaje;
- exponer endpoints para que Next.js construya el inbox.

## Modulos involucrados

- `contacts`
- `conversations`
- `audit`
- `core`

## Contactos

Modelos:

- `contacts_contact`;
- `contacts_contact_phone`;
- `contacts_contact_email`;
- `contacts_company`;
- `contacts_contact_company`;
- `contacts_contact_tag`;
- `contacts_contact_note`;
- `contacts_contact_event`.

### Contact

Campos:

- `id`;
- `organization_id`;
- `display_name`;
- `first_name`;
- `last_name`;
- `company_name`;
- `source`;
- `type`;
- `status`;
- `language`;
- `timezone`;
- `avatar_url`;
- `summary`;
- `metadata`;
- `created_at`;
- `updated_at`.

Tipos:

- `unknown`;
- `lead`;
- `client`;
- `internal`;
- `supplier`;
- `blocked`.

Estados:

- `active`;
- `inactive`;
- `blocked`;
- `archived`.

### ContactPhone

Campos:

- `id`;
- `organization_id`;
- `contact_id`;
- `phone_e164`;
- `country_code`;
- `is_primary`;
- `is_whatsapp`;
- `verified_at`;
- `metadata`.

Reglas:

- todo telefono se normaliza a E.164;
- no puede haber duplicados por organizacion;
- un contacto puede tener multiples telefonos;
- un telefono primario por contacto;
- resolver contacto por telefono debe ser deterministico.

### ContactNote

Campos:

- `id`;
- `organization_id`;
- `contact_id`;
- `author_id`;
- `body`;
- `visibility`;
- `created_at`;
- `updated_at`.

Visibilidad inicial:

- `internal`;
- `team`;
- `private`.

## Empresas

Modelo:

```text
contacts_company
```

Campos:

- `id`;
- `organization_id`;
- `name`;
- `website`;
- `industry`;
- `size`;
- `country`;
- `metadata`;
- `created_at`;
- `updated_at`.

Esto permite vender a personas o empresas y soporta relaciones futuras B2B.

## Conversaciones

Modelo:

```text
conversations_conversation
```

Campos:

- `id`;
- `organization_id`;
- `contact_id`;
- `channel`;
- `status`;
- `mode`;
- `assigned_user_id`;
- `ai_enabled`;
- `last_message_at`;
- `last_inbound_at`;
- `last_outbound_at`;
- `summary`;
- `metadata`;
- `created_at`;
- `updated_at`.

Canales:

- `whatsapp`;
- `email`;
- `dashboard`;
- `system`.

Modos:

- `sales_ai`;
- `support_ai`;
- `internal_assistant`;
- `manual`;
- `paused`;
- `blocked`.

Estados:

- `open`;
- `pending`;
- `closed`;
- `archived`.

## Mensajes

Modelo:

```text
conversations_message
```

Campos:

- `id`;
- `organization_id`;
- `conversation_id`;
- `contact_id`;
- `direction`;
- `message_type`;
- `body`;
- `normalized_text`;
- `external_message_id`;
- `external_timestamp`;
- `status`;
- `raw_payload`;
- `metadata`;
- `created_at`.

Direcciones:

- `inbound`;
- `outbound`;
- `internal`;
- `system`.

Tipos:

- `text`;
- `audio`;
- `image`;
- `document`;
- `video`;
- `sticker`;
- `location`;
- `contact_card`;
- `system`.

Estados:

- `received`;
- `processed`;
- `queued`;
- `sent`;
- `delivered`;
- `read`;
- `failed`;
- `ignored`.

## Attachments

Modelo:

```text
conversations_message_attachment
```

Campos:

- `id`;
- `organization_id`;
- `message_id`;
- `media_asset_id`;
- `external_media_id`;
- `mime_type`;
- `file_name`;
- `size_bytes`;
- `metadata`;
- `created_at`.

En esta fase puede existir sin descarga real de media. Lo importante es que el modelo de mensaje soporte adjuntos desde el principio.

## Resumenes de conversacion

Modelo:

```text
conversations_conversation_summary
```

Campos:

- `id`;
- `organization_id`;
- `conversation_id`;
- `summary`;
- `summary_type`;
- `source_message_from_id`;
- `source_message_to_id`;
- `created_by_ai_run_id`;
- `created_at`.

Tipos:

- `short`;
- `technical`;
- `sales`;
- `support`;
- `daily`;
- `handoff`.

## Memoria conversacional

Modelo:

```text
conversations_conversation_memory
```

Campos:

- `id`;
- `organization_id`;
- `conversation_id`;
- `contact_id`;
- `memory_type`;
- `content`;
- `importance`;
- `embedding_id`;
- `source_message_id`;
- `expires_at`;
- `created_at`.

Tipos:

- `preference`;
- `pain_point`;
- `technical_context`;
- `commercial_context`;
- `support_context`;
- `objection`;
- `commitment`.

## Servicios

Servicios esperados:

- `ContactResolver`;
- `ContactMerger`;
- `ContactClassifier`;
- `ConversationResolver`;
- `MessageIngestionService`;
- `MessageNormalizer`;
- `ConversationRouter`;
- `ConversationSummaryService`;
- `ConversationMemoryService`;
- `ConversationHandoffService`.

## ConversationRouter

Debe decidir:

- si el contacto es lead;
- si el contacto es cliente;
- si el contacto es interno;
- si la conversacion esta pausada;
- si debe responder IA;
- si debe quedar manual;
- si debe derivar a humano.

En esta fase puede usar reglas simples:

```text
contact.type == client   -> support_ai
contact.type == lead     -> sales_ai
contact.type == internal -> internal_assistant
ai_enabled == false      -> manual
conversation.paused      -> paused
```

## Endpoints

```text
GET    /api/v1/contacts/
POST   /api/v1/contacts/
GET    /api/v1/contacts/{id}/
PATCH  /api/v1/contacts/{id}/
DELETE /api/v1/contacts/{id}/

POST   /api/v1/contacts/{id}/notes/
POST   /api/v1/contacts/{id}/tags/
POST   /api/v1/contacts/merge/

GET    /api/v1/conversations/
GET    /api/v1/conversations/{id}/
GET    /api/v1/conversations/{id}/messages/

POST   /api/v1/conversations/{id}/send-message/
POST   /api/v1/conversations/{id}/takeover/
POST   /api/v1/conversations/{id}/pause-ai/
POST   /api/v1/conversations/{id}/resume-ai/
POST   /api/v1/conversations/{id}/close/
POST   /api/v1/conversations/{id}/reopen/
```

## Eventos internos

- `contact.created.v1`;
- `contact.updated.v1`;
- `conversation.created.v1`;
- `conversation.mode_changed.v1`;
- `conversation.message_received.v1`;
- `conversation.message_sent.v1`;
- `conversation.handoff_requested.v1`.

## Tests obligatorios

- `test_contact_created`;
- `test_contact_phone_normalized`;
- `test_duplicate_phone_resolves_existing_contact`;
- `test_conversation_created_for_contact`;
- `test_message_ingestion`;
- `test_message_external_id_deduplication`;
- `test_conversation_router_for_lead`;
- `test_conversation_router_for_client`;
- `test_pause_ai`;
- `test_resume_ai`;
- `test_takeover_sets_manual_mode`.

## Criterios de perfeccion

La fase 3 esta perfecta cuando:

1. Cada contacto puede tener multiples telefonos.
2. Los telefonos se normalizan.
3. No se duplican contactos por mismo numero.
4. Cada mensaje pertenece a una conversacion.
5. Cada conversacion pertenece a un contacto.
6. Cada conversacion tiene modo operativo.
7. Se puede pausar o reactivar IA.
8. Se puede tomar control manual.
9. Existe historial completo de mensajes.
10. Existe estructura de attachments.
11. Existe estructura de resumenes.
12. Existe estructura de memoria.
13. Los endpoints del inbox estan listos para Next.js.
14. Hay eventos internos por mensaje y conversacion.
15. Hay tests de deduplicacion y ruteo.

## Riesgos a evitar

- guardar telefono sin normalizar;
- deduplicar por nombre en vez de telefono;
- mezclar lead/client directamente en Conversation;
- crear inbox sin estados claros;
- permitir mensajes sin conversation;
- no guardar raw_payload cuando venga de proveedor;
- no tener takeover manual.

## Recomendacion de division en subfases

### Fase 3.1: Contactos y telefonos

Entregables:

- Contact;
- ContactPhone;
- normalizador E.164;
- ContactResolver;
- endpoints CRUD.

Validacion:

- tests de normalizacion;
- tests de duplicados;
- tests de busqueda por telefono.

### Fase 3.2: Empresas, notas y tags

Entregables:

- Company;
- ContactCompany;
- ContactNote;
- tags;
- endpoints secundarios.

Validacion:

- tests de relacion contacto-empresa;
- tests de notas con autor;
- tests de permisos.

### Fase 3.3: Conversaciones

Entregables:

- Conversation;
- ConversationResolver;
- estados;
- modos;
- pause/resume/takeover/close/reopen.

Validacion:

- tests de creacion;
- tests de cambio de modo;
- tests de takeover manual.

### Fase 3.4: Mensajes y attachments

Entregables:

- Message;
- MessageAttachment;
- MessageIngestionService;
- deduplicacion por external_message_id.

Validacion:

- tests de inbound;
- tests de outbound interno;
- tests de duplicados;
- tests de attachment.

### Fase 3.5: Router, resumenes y memoria

Entregables:

- ConversationRouter;
- ConversationSummary;
- ConversationMemory;
- eventos internos.

Validacion:

- tests de lead/client/internal/manual;
- tests de eventos outbox;
- tests de resumen/memoria base.

### Fase 3.6: Contrato de inbox para Next.js

Entregables:

- endpoints optimizados;
- filtros por estado/modo/canal;
- orden por last_message_at;
- paginacion;
- serializers livianos para listado y detalle.

Validacion:

- tests API;
- OpenAPI actualizado;
- payload suficiente para UI sin N+1 queries.
