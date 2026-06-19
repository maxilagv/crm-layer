# Fase 7: Clientes, soporte, tickets, audios y media

## Objetivo

Construir el modo cliente/soporte. Si un numero pertenece a un cliente registrado, el sistema deja de vender y pasa a asistir.

Esta fase incluye audios, transcripciones, capturas, archivos, tickets y generacion de assets basicos.

## Resultado esperado

Al terminar esta fase el backend debe poder:

- registrar clientes separados de leads;
- rutear numeros de clientes a soporte;
- crear tickets desde texto;
- crear tickets desde audio;
- descargar media de WhatsApp;
- guardar archivos en storage privado;
- transcribir audios;
- resumir tecnicamente problemas;
- clasificar prioridad y categoria;
- responder al cliente con confirmacion;
- notificar tickets urgentes;
- generar y guardar imagenes/assets;
- entregar signed URLs temporales.

## Modulos involucrados

- `clients`
- `support`
- `media`
- `ai`
- `whatsapp`
- `conversations`
- `notifications`
- `audit`
- `settings`

## Modelos de clientes

Modelos esperados:

- `clients_client`;
- `clients_client_contact`;
- `clients_client_service`;
- `clients_client_status_history`.

### Client

Campos:

- `id`;
- `organization_id`;
- `contact_id`;
- `company_id`;
- `display_name`;
- `status`;
- `service_plan`;
- `support_level`;
- `onboarding_status`;
- `started_at`;
- `ended_at`;
- `metadata`;
- `created_at`;
- `updated_at`.

Estados:

- `active`;
- `paused`;
- `cancelled`;
- `onboarding`;
- `delinquent`;
- `archived`.

Support levels:

- `standard`;
- `priority`;
- `vip`;
- `internal`.

## Modelos de soporte

Modelos esperados:

- `support_ticket`;
- `support_ticket_event`;
- `support_ticket_comment`;
- `support_ticket_attachment`;
- `support_known_issue`;
- `support_resolution`.

### SupportTicket

Campos:

- `id`;
- `organization_id`;
- `client_id`;
- `contact_id`;
- `conversation_id`;
- `source_message_id`;
- `status`;
- `priority`;
- `category`;
- `title`;
- `description`;
- `technical_summary`;
- `ai_summary`;
- `assigned_user_id`;
- `due_at`;
- `resolved_at`;
- `metadata`;
- `created_at`;
- `updated_at`.

Estados:

- `open`;
- `waiting_client`;
- `triaged`;
- `in_progress`;
- `blocked`;
- `resolved`;
- `closed`;
- `cancelled`.

Prioridades:

- `low`;
- `medium`;
- `high`;
- `urgent`;
- `critical`.

Categorias:

- `bug`;
- `access`;
- `billing`;
- `feature_request`;
- `integration`;
- `performance`;
- `data_issue`;
- `unknown`.

## Modelos de media

Modelos esperados:

- `media_media_asset`;
- `media_transcription`;
- `media_processing_job`;
- `media_image_generation_request`;
- `media_generated_image`.

### MediaAsset

Campos:

- `id`;
- `organization_id`;
- `owner_type`;
- `owner_id`;
- `file_name`;
- `mime_type`;
- `size_bytes`;
- `storage_key`;
- `storage_provider`;
- `checksum`;
- `source`;
- `status`;
- `metadata`;
- `created_at`.

Sources:

- `whatsapp`;
- `dashboard`;
- `ai_generated`;
- `system`.

Statuses:

- `pending`;
- `stored`;
- `processing`;
- `processed`;
- `failed`;
- `deleted`.

### Transcription

Campos:

- `id`;
- `organization_id`;
- `media_asset_id`;
- `provider`;
- `model`;
- `language`;
- `text`;
- `confidence`;
- `duration_seconds`;
- `status`;
- `error_message`;
- `created_at`.

## Servicios

Servicios esperados:

- `ClientResolver`;
- `ClientRegistrationService`;
- `ClientContactService`;
- `SupportTicketCreator`;
- `SupportTriageService`;
- `SupportReplyService`;
- `TicketLifecycleService`;
- `KnownIssueMatcher`;
- `MediaStorageService`;
- `MediaDownloader`;
- `AudioTranscriptionService`;
- `AudioTicketExtractor`;
- `ImageGenerationService`;
- `GeneratedAssetStorage`.

## Flujo cliente perfecto

```text
cliente escribe
|
contact resolver identifica numero como cliente
|
conversation router activa support_ai
|
support agent interpreta mensaje
|
si es problema, crea ticket
|
si falta informacion, pregunta
|
si es urgente, notifica al owner
|
todo queda en historial
```

## Flujo audio perfecto

```text
cliente manda audio
|
WhatsApp registra mensaje
|
media downloader descarga archivo
|
media asset guarda audio
|
transcription worker transcribe
|
audio ticket extractor resume problema
|
support ticket se crea
|
cliente recibe confirmacion
|
owner recibe resumen por WhatsApp
```

## Output esperado del extractor de audio

```json
{
  "title": "Error de login al ingresar contrasena",
  "description": "El cliente indica que no puede iniciar sesion...",
  "category": "access",
  "priority": "medium",
  "missing_information": [
    "captura del error",
    "email usado para iniciar sesion"
  ],
  "suggested_reply": "Recibido. Para revisarlo mas rapido, mandame una captura del error y el email con el que intentas ingresar.",
  "owner_summary": "Cliente X reporta error de login. Falta captura y email."
}
```

## Reglas del agente soporte

Debe:

- confirmar recepcion;
- pedir informacion faltante;
- crear ticket;
- clasificar urgencia;
- ser claro;
- ser calmo;
- evitar prometer resolucion inmediata;
- notificar al owner si es urgente.

No debe:

- pedir contrasenas;
- pedir tokens privados;
- exponer datos de otros clientes;
- cerrar tickets criticos solo;
- modificar produccion sin permiso;
- decir que algo esta resuelto sin evidencia.

## Generacion de imagenes

En esta fase puede incorporarse el backend para generar assets.

Tipos:

- `proposal_cover`;
- `instagram_post`;
- `instagram_story`;
- `banner`;
- `thumbnail`;
- `ad_creative`;
- `client_mockup`.

Endpoints:

```text
POST /api/v1/image-generations/
GET  /api/v1/image-generations/
GET  /api/v1/image-generations/{id}/
POST /api/v1/image-generations/{id}/send-to-contact/
```

## Endpoints clientes y soporte

```text
GET   /api/v1/clients/
POST  /api/v1/clients/
GET   /api/v1/clients/{id}/
PATCH /api/v1/clients/{id}/

GET   /api/v1/tickets/
POST  /api/v1/tickets/
GET   /api/v1/tickets/{id}/
PATCH /api/v1/tickets/{id}/

POST  /api/v1/tickets/{id}/assign/
POST  /api/v1/tickets/{id}/resolve/
POST  /api/v1/tickets/{id}/reopen/
POST  /api/v1/tickets/{id}/comments/

GET   /api/v1/media/assets/
POST  /api/v1/media/assets/
GET   /api/v1/media/assets/{id}/
GET   /api/v1/media/assets/{id}/download-url/

POST  /api/v1/media/transcriptions/
POST  /api/v1/image-generations/
```

## Workers

- `media.download_whatsapp_media`;
- `media.process_audio`;
- `media.transcribe_audio`;
- `support.create_ticket_from_audio`;
- `support.triage_ticket`;
- `support.generate_support_reply`;
- `support.notify_owner_for_urgent_ticket`;
- `media.generate_image`;
- `media.store_generated_image`.

## Tests obligatorios

- `test_registered_contact_routes_to_support`;
- `test_client_message_creates_ticket`;
- `test_audio_message_downloads_media`;
- `test_audio_transcription_created`;
- `test_ticket_from_audio_created`;
- `test_support_agent_does_not_request_password`;
- `test_urgent_ticket_notifies_owner`;
- `test_ticket_status_lifecycle`;
- `test_media_asset_private_storage`;
- `test_generated_image_is_stored`.

## Criterios de perfeccion

La fase 7 esta perfecta cuando:

1. Los clientes estan separados de leads.
2. Un numero cliente activa soporte, no ventas.
3. Los tickets tienen prioridad y categoria.
4. Los audios se descargan correctamente.
5. Los audios se transcriben.
6. Los audios pueden crear tickets.
7. Las capturas y documentos quedan asociados.
8. El soporte pide datos faltantes.
9. El soporte no pide secretos.
10. Los tickets urgentes notifican al owner.
11. Hay storage privado.
12. Hay signed URLs para descargas.
13. Las imagenes generadas se guardan como assets.
14. Todo queda auditado.
15. Hay tests de flujo completo.

## Riesgos a evitar

- rutear clientes a ventas;
- descargar archivos en request;
- guardar archivos publicos sin signed URL;
- pedir passwords;
- cerrar tickets automaticamente sin evidencia;
- generar imagenes dentro del flujo critico de WhatsApp;
- no validar MIME/size/checksum.

## Recomendacion de division en subfases

### Fase 7.1: Clientes

Entregables:

- Client;
- ClientContact;
- ClientService;
- ClientResolver;
- endpoints CRUD.

Validacion:

- contacto cliente rutea a soporte;
- lead convertido no queda duplicado;
- status history.

### Fase 7.2: Tickets

Entregables:

- SupportTicket;
- TicketEvent;
- comments;
- attachments;
- lifecycle.

Validacion:

- ticket creado;
- assign/resolve/reopen;
- prioridad y categoria.

### Fase 7.3: Media storage

Entregables:

- MediaAsset;
- storage service;
- private bucket;
- signed URLs;
- MIME/size/checksum validation.

Validacion:

- asset privado;
- URL temporal;
- archivo invalido rechazado.

### Fase 7.4: Audio pipeline

Entregables:

- media downloader;
- transcription model;
- AudioTranscriptionService;
- chunking si aplica;
- retries.

Validacion:

- audio descargado;
- transcripcion creada;
- fallo reintentable.

### Fase 7.5: Ticket desde audio

Entregables:

- prompt audio_ticket_extraction;
- structured output;
- SupportTicketCreator;
- owner summary.

Validacion:

- ticket creado desde transcript;
- missing information;
- prioridad correcta.

### Fase 7.6: Support agent

Entregables:

- SupportReplyService;
- SupportPolicy;
- SafetyGuard soporte;
- WhatsApp response.

Validacion:

- no pide secretos;
- pide datos faltantes;
- urgente notifica.

### Fase 7.7: Image generation

Entregables:

- ImageGenerationRequest;
- GeneratedImage;
- generate/store;
- send-to-contact opcional.

Validacion:

- asset generado;
- guardado privado;
- historial en media.
