# Principios del backend

## 1. Modular monolith primero

El backend debe ser un monolito modular. Esto significa:

- un deploy principal;
- una base de datos principal;
- modulos internos bien separados;
- contratos claros entre modulos;
- services/selectors por modulo;
- eventos internos para desacoplar flujos;
- posibilidad real de extraer modulos en el futuro.

No se crean microservicios en la primera etapa porque agregarian costo operativo, problemas de consistencia y complejidad de despliegue antes de validar el producto.

## 2. PostgreSQL es la fuente de verdad

Todo dato importante se persiste en PostgreSQL:

- eventos crudos de WhatsApp;
- contactos;
- mensajes;
- tickets;
- tareas;
- decisiones IA;
- prompts;
- costos;
- auditoria;
- estados de envio.

Redis, Celery, caches y proveedores externos son auxiliares. Si Redis cae, el sistema no debe perder la verdad del negocio.

## 3. Event-driven interno

Las acciones importantes generan eventos internos persistidos con outbox.

Ejemplo:

```text
message inbound guardado
|
outbox event: conversation.message_received.v1
|
worker procesa scoring, respuesta, tareas, tickets o notificaciones
```

El objetivo es evitar que una request HTTP haga todo, y evitar perder trabajos cuando Celery o Redis fallen temporalmente.

## 4. Idempotencia por defecto

WhatsApp reintenta webhooks. Celery reintenta jobs. El frontend puede reenviar requests. Por eso las operaciones criticas deben ser idempotentes.

Se deduplica por:

- webhook event id;
- external message id;
- idempotency key HTTP;
- media id;
- outbound message id;
- task/job correlation id.

## 5. IA como plataforma interna, no llamadas sueltas

Ningun modulo llama directamente a OpenAI o Anthropic.

Todo pasa por `ai`:

- proveedor;
- modelo;
- prompt;
- schema de salida;
- safety guard;
- tool permissions;
- costo;
- auditoria;
- fallback;
- evals.

## 6. WhatsApp como proveedor reemplazable

El resto del sistema no debe conocer payloads crudos de Meta, tokens, endpoints ni detalles de plantillas.

El modulo `whatsapp` traduce:

- webhooks crudos a mensajes normalizados;
- mensajes internos a payloads de Meta;
- statuses de Meta a estados propios;
- media references a media assets privados.

## 7. Seguridad por diseno

Desde el inicio:

- organization_id en recursos importantes;
- permisos por accion;
- API keys hasheadas;
- webhooks firmados;
- logs sin secretos;
- soft delete;
- auditoria;
- rate limits;
- validacion de archivos;
- URLs firmadas temporales;
- separacion de datos por organizacion.

## 8. Observabilidad desde temprano

Cada request y flujo asincronico debe tener:

- request_id;
- correlation_id;
- organization_id;
- user_id cuando exista;
- contact_id/conversation_id/message_id cuando aplique;
- ai_run_id cuando aplique;
- task_id/job_id cuando aplique.

Si algo falla, el backend debe permitir responder: que paso, cuando, con que input, que proveedor fallo, si se reintento y que estado quedo.
