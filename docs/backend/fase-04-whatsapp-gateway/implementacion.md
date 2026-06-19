# Implementacion Fase 4

## Alcance implementado

La Fase 4 agrega el modulo `crm.whatsapp` como gateway aislado para WhatsApp
Cloud API. El resto del CRM trabaja con contactos, conversaciones, mensajes,
outbox y auditoria; no conoce endpoints, tokens ni payloads crudos de Meta.

## Arquitectura

Capas creadas:

- `crm.whatsapp.models`: persistencia del gateway.
- `crm.whatsapp.domain`: enums, eventos internos y politicas.
- `crm.whatsapp.clients`: clients de Meta, media y templates, todos fakeables.
- `crm.whatsapp.services`: verification, webhook persistence, inbound, outbound,
  media, statuses y templates.
- `crm.whatsapp.tasks`: workers Celery.
- `crm.whatsapp.api`: webhook publico y endpoints internos.

## Modelos

Tablas:

- `whatsapp_business_account`;
- `whatsapp_phone_number`;
- `whatsapp_webhook_event`;
- `whatsapp_inbound_message`;
- `whatsapp_outbound_message`;
- `whatsapp_message_status`;
- `whatsapp_template`;
- `whatsapp_media_reference`.

Todas las tablas principales incluyen `organization_id`. Los uniques cubren:

- organizacion + WABA;
- organizacion + phone number id;
- organizacion + webhook event id;
- organizacion + external inbound message id;
- organizacion + outbound idempotency key;
- organizacion + external media id;
- organizacion + template name/language;
- organizacion + external status/status/timestamp.

## Webhook

`GET /api/v1/webhooks/whatsapp/`:

- lee `hub.mode`, `hub.verify_token`, `hub.challenge`;
- compara token con `hmac.compare_digest`;
- responde el challenge plano, sin envelope;
- en fallo responde 403 y audita sin exponer token.

`POST /api/v1/webhooks/whatsapp/`:

- valida `X-Hub-Signature-256`;
- calcula HMAC SHA-256 con `WHATSAPP_APP_SECRET`;
- usa `request.body` crudo;
- compara con `hmac.compare_digest`;
- guarda `raw_payload` completo en `WhatsAppWebhookEvent`;
- trunca la firma guardada;
- deduplica por `organization_id + event_id`;
- responde 200 rapido;
- encola `whatsapp.process_webhook_event`;
- no descarga media;
- no llama IA;
- no llama Meta.

## Inbound

El parser soporta `entry -> changes -> value -> messages/statuses`.

Mensajes inbound:

- resuelven organizacion desde `phone_number_id`;
- resuelven/crean contacto via `ContactResolver`;
- resuelven/crean conversacion WhatsApp;
- crean `conversations.Message` normalizado;
- guardan fragmento Meta en `WhatsAppInboundMessage.raw_message`;
- no guardan el payload completo Meta en `conversations.Message.raw_payload`;
- emiten `conversation.message_received.v1` por outbox;
- crean `WhatsAppMediaReference` y `MessageAttachment` para audio/imagen/documento/video/sticker.

## Outbound

Outbound se persiste antes de llamar Meta:

1. service crea `WhatsAppOutboundMessage` en `queued`;
2. se crea `conversations.Message` outbound en `queued`;
3. se encola `whatsapp.send_outbound_message`;
4. worker cambia `queued/failed -> sending`;
5. worker llama `MetaClient`;
6. exito guarda `external_message_id`, `sent_at`, `response_payload` sanitizado;
7. error guarda `failed_at`, `error_code`, `error_message` sanitizado.

Los endpoints HTTP internos no llaman Meta.

## Media

El webhook nunca descarga media.

Flujo:

1. inbound crea `WhatsAppMediaReference` en `queued`;
2. se crea `MessageAttachment`;
3. se encola `whatsapp.download_media`;
4. worker usa `MediaClient`;
5. se marca `downloaded` o `failed`;
6. no se persisten ni exponen URLs temporales.

El modulo de media asset privado aun no existe. La integracion queda documentada
como pendiente en metadata (`media_asset_integration: pending`).

## Status

Status webhooks:

- crean historial en `WhatsAppMessageStatus`;
- actualizan `WhatsAppOutboundMessage`;
- `delivered` setea `delivered_at`;
- `read` setea `read_at` y tambien `delivered_at` si falta;
- `failed` setea `failed_at`, `error_code`, `error_message`;
- status duplicado no duplica historial;
- status desconocido se guarda como `unknown` sin romper.

## Templates

Implementado:

- modelo `WhatsAppTemplate`;
- unique `organization_id + name + language`;
- `GET /api/v1/whatsapp/templates/`;
- `POST /api/v1/whatsapp/templates/send/`;
- `sync_templates_for_organization` con `TemplateClient` fakeable;
- worker `whatsapp.sync_templates`.

## Endpoints internos

Todos requieren auth, organizacion actual y permisos server-side:

- `GET /api/v1/whatsapp/templates/` -> `settings.manage`;
- `POST /api/v1/whatsapp/templates/send/` -> `conversations.reply`;
- `GET /api/v1/whatsapp/outbound-messages/` -> `conversations.view`;
- `GET /api/v1/whatsapp/webhook-events/` -> `audit.view`.

`webhook-events` no expone `raw_payload` por defecto. Solo lo incluye con
`include_raw=true` en endpoint protegido por `audit.view`.

## Workers

Workers implementados:

- `whatsapp.process_webhook_event`;
- `whatsapp.handle_inbound_message`;
- `whatsapp.download_media`;
- `whatsapp.send_outbound_message`;
- `whatsapp.update_message_status`;
- `whatsapp.sync_templates`.

Los workers usan base de datos como fuente de verdad. Redis/Celery solo encolan.
Los retries son acotados (`max_retries=3`) y usan backoff simple hasta 300s.
Outbound y media persisten el estado `failed` antes de propagar errores
transitorios al worker, de modo que los reintentos sean seguros e idempotentes.
Template sync reintenta solo errores marcados como transitorios por el client.

## Tests

Archivo principal:

```text
apps/api/tests/api/test_whatsapp_gateway.py
```

Cobertura:

- verificacion webhook exitosa/fallida;
- firma invalida;
- guardado de raw event;
- duplicado de webhook;
- inbound texto;
- inbound audio + media reference;
- outbound queued;
- outbound sent;
- delivered status;
- failed status;
- error de Meta al enviar;
- media downloader con fake client;
- template sync con fake client;
- template send;
- raw payload oculto por defecto.

## Revision critica por matriz

Estado: todas las respuestas criticas quedan cubiertas por implementacion o test.

Deudas documentadas:

- el modulo privado de media asset aun no existe;
- `WhatsAppMediaReference` queda asociado a `MessageAttachment` y deja metadata
  de integracion pendiente;
- PostgreSQL local de esta maquina rechaza `ai_crm/ai_crm`, por lo que la suite
  oficial no puede ejecutarse hasta corregir credenciales o levantar Docker.

## Validacion

Ejecutado correctamente:

```bash
ruff check .
python manage.py check --settings=crm.config.settings.test
python manage.py makemigrations --check --dry-run --settings=crm.config.settings.test
python manage.py spectacular --file ../../docs/api/openapi.yaml --settings=crm.config.settings.test
```

Validacion temporal por limitacion de entorno:

```bash
DATABASE_URL=sqlite:///.../.tmp-whatsapp.sqlite3 pytest tests/api/test_whatsapp_gateway.py -q
DATABASE_URL=sqlite:///.../.tmp-whatsapp-migrate.sqlite3 python manage.py migrate --settings=crm.config.settings.test --noinput
```

Resultado:

- tests WhatsApp: 16 passed;
- migraciones aplican en SQLite;
- OpenAPI: 0 errores, warnings menores de nombres de enums.

Bloqueado por entorno:

```bash
pytest tests/api/test_whatsapp_gateway.py -q
```

Falla antes de ejecutar tests porque PostgreSQL local rechaza:

```text
postgres://ai_crm:ai_crm@localhost:5432/ai_crm
```
