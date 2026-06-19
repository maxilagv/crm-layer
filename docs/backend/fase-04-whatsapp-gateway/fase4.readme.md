# Fase 4: WhatsApp Gateway completo

Documento de implementacion actual: [implementacion.md](implementacion.md).

## Objetivo

Integrar WhatsApp de forma profesional usando un modulo aislado. El resto del sistema no debe saber como funciona Meta, ni tokens, ni endpoints, ni payloads crudos.

WhatsApp debe ser tratado como un proveedor externo reemplazable.

## Resultado esperado

Al terminar esta fase el backend debe poder:

- verificar webhook de Meta;
- validar firma de eventos;
- guardar payload crudo;
- deduplicar webhooks;
- responder rapido a Meta;
- procesar eventos en workers;
- convertir mensajes WhatsApp en mensajes normalizados;
- enviar mensajes outbound;
- registrar estados sent/delivered/read/failed;
- manejar media references;
- descargar media en workers;
- modelar plantillas;
- exponer endpoints internos de supervision.

## Modulos involucrados

- `whatsapp`
- `conversations`
- `contacts`
- `media`
- `notifications` basico
- `audit`

## Estructura del modulo

```text
crm/modules/whatsapp/
|-- models.py
|-- api/
|   |-- webhook_views.py
|   |-- serializers.py
|   \-- urls.py
|-- clients/
|   |-- meta_client.py
|   |-- media_client.py
|   \-- template_client.py
|-- services/
|   |-- webhook_verification.py
|   |-- inbound_message_handler.py
|   |-- outbound_message_sender.py
|   |-- media_downloader.py
|   |-- message_status_handler.py
|   \-- template_sender.py
|-- domain/
|   |-- enums.py
|   |-- events.py
|   \-- policies.py
|-- tasks.py
\-- tests/
```

## Modelos

Modelos esperados:

- `whatsapp_business_account`;
- `whatsapp_phone_number`;
- `whatsapp_webhook_event`;
- `whatsapp_inbound_message`;
- `whatsapp_outbound_message`;
- `whatsapp_message_status`;
- `whatsapp_template`;
- `whatsapp_media_reference`.

### WhatsAppBusinessAccount

Campos:

- `id`;
- `organization_id`;
- `waba_id`;
- `name`;
- `status`;
- `metadata`;
- `created_at`;
- `updated_at`.

### WhatsAppPhoneNumber

Campos:

- `id`;
- `organization_id`;
- `business_account_id`;
- `phone_number_id`;
- `display_phone_number`;
- `verified_name`;
- `status`;
- `metadata`;
- `created_at`;
- `updated_at`.

### WhatsAppWebhookEvent

Campos:

- `id`;
- `organization_id`;
- `event_id`;
- `event_type`;
- `raw_payload`;
- `signature`;
- `status`;
- `received_at`;
- `processed_at`;
- `error_message`;
- `created_at`.

Estados:

- `received`;
- `processing`;
- `processed`;
- `failed`;
- `ignored`;
- `duplicate`.

### WhatsAppOutboundMessage

Campos:

- `id`;
- `organization_id`;
- `conversation_id`;
- `contact_id`;
- `message_type`;
- `body`;
- `template_name`;
- `external_message_id`;
- `status`;
- `sent_at`;
- `delivered_at`;
- `read_at`;
- `failed_at`;
- `error_code`;
- `error_message`;
- `metadata`;
- `created_at`.

## Endpoints publicos

```text
GET  /api/v1/webhooks/whatsapp/
POST /api/v1/webhooks/whatsapp/
```

`GET` valida el webhook.

`POST` recibe eventos. Debe ser rapido: validar, guardar, deduplicar, encolar y responder.

## Endpoints internos

```text
GET  /api/v1/whatsapp/templates/
POST /api/v1/whatsapp/templates/send/
GET  /api/v1/whatsapp/outbound-messages/
GET  /api/v1/whatsapp/webhook-events/
```

## Flujo inbound perfecto

```text
WhatsApp envia webhook
|
backend valida token/firma
|
backend guarda raw_payload
|
backend deduplica evento
|
backend responde rapido a Meta
|
worker procesa evento
|
se resuelve contacto por telefono
|
se crea/actualiza conversacion
|
se crea mensaje normalizado
|
si hay media, se registra referencia
|
se emite evento conversation.message_received.v1
```

## Flujo outbound perfecto

```text
modulo de negocio solicita enviar mensaje
|
whatsapp_outbound_message se crea en estado queued
|
worker llama Meta API
|
se guarda external_message_id
|
estado pasa a sent
|
webhook posterior actualiza delivered/read/failed
```

## Media inbound

Cuando llegue audio, imagen o documento:

1. Guardar mensaje.
2. Guardar referencia externa de media.
3. Crear job de descarga.
4. Descargar media en worker.
5. Guardar en media asset privado.
6. Asociar attachment al mensaje.

Nunca se descarga media dentro del request del webhook.

## Plantillas

Debe soportar:

- templates de utilidad;
- templates de marketing si aplica;
- templates de recordatorio interno;
- templates de seguimiento.

Modelo:

```text
whatsapp_template
```

Campos:

- `id`;
- `organization_id`;
- `name`;
- `language`;
- `category`;
- `status`;
- `components`;
- `metadata`;
- `created_at`;
- `updated_at`.

## Workers

- `whatsapp.process_webhook_event`;
- `whatsapp.handle_inbound_message`;
- `whatsapp.download_media`;
- `whatsapp.send_outbound_message`;
- `whatsapp.update_message_status`;
- `whatsapp.sync_templates`.

## Idempotencia obligatoria

Se debe deduplicar por:

- webhook event id;
- external message id;
- outbound idempotency key;
- media id.

## Tests obligatorios

- `test_webhook_verification_success`;
- `test_webhook_verification_failure`;
- `test_webhook_post_saves_raw_event`;
- `test_duplicate_webhook_is_ignored`;
- `test_inbound_text_creates_message`;
- `test_inbound_audio_creates_media_reference`;
- `test_outbound_message_queued`;
- `test_outbound_message_sent`;
- `test_message_status_delivered_updates_record`;
- `test_failed_message_stores_error_code`.

## Criterios de perfeccion

La fase 4 esta perfecta cuando:

1. El webhook se valida correctamente.
2. Todo payload crudo se guarda.
3. Los eventos duplicados no duplican mensajes.
4. El webhook responde rapido.
5. El procesamiento ocurre en workers.
6. Los mensajes entrantes crean contactos/conversaciones/mensajes.
7. Los audios e imagenes crean referencias de media.
8. Los mensajes salientes tienen estado.
9. Los delivery/read receipts actualizan estado.
10. Las plantillas estan modeladas.
11. WhatsApp esta aislado del resto del backend.
12. Hay retries controlados.
13. Hay logs y auditoria.
14. Hay tests con payloads reales simulados.

## Riesgos a evitar

- descargar media en el webhook;
- responder lento a Meta;
- mezclar payload crudo de Meta en conversations;
- no validar firma;
- duplicar mensajes por reintentos;
- enviar mensajes desde modulos de negocio sin pasar por WhatsApp Gateway;
- no persistir outbound antes de llamar API externa.

## Recomendacion de division en subfases

### Fase 4.1: Webhook verification

Entregables:

- endpoint GET;
- verify token;
- endpoint POST;
- signature validator;
- modelo webhook event.

Validacion:

- tests de token correcto/incorrecto;
- tests de firma correcta/incorrecta;
- payload crudo persistido.

### Fase 4.2: Deduplicacion y workers inbound

Entregables:

- event_id resolver;
- estado duplicate;
- worker `process_webhook_event`;
- locking;
- error handling.

Validacion:

- tests de webhook duplicado;
- test de worker idempotente;
- test de evento failed.

### Fase 4.3: Mensajes inbound normalizados

Entregables:

- parser de payload Meta;
- handler texto;
- resolver de contacto;
- resolver de conversacion;
- creacion de message;
- evento outbox `conversation.message_received.v1`.

Validacion:

- payload real simulado;
- mensaje creado;
- contacto creado;
- conversacion creada;
- no duplicacion por external_message_id.

### Fase 4.4: Media references y descarga asincronica

Entregables:

- media reference;
- job de descarga;
- Meta media client;
- asociacion con media asset;
- status de descarga.

Validacion:

- audio crea media reference;
- worker descarga fake media;
- attachment asociado;
- reintento en error.

### Fase 4.5: Outbound messages

Entregables:

- service `OutboundMessageSender`;
- modelo outbound;
- cola outbound;
- Meta client;
- estados queued/sent/failed.

Validacion:

- mensaje queued;
- fake Meta devuelve external id;
- error guarda code/message;
- idempotencia outbound.

### Fase 4.6: Status webhooks y templates

Entregables:

- status handler;
- delivered/read/failed;
- modelo template;
- sync templates;
- send template.

Validacion:

- status actualiza outbound;
- template listado;
- template enviado;
- auditoria de fallos.
