# Fase 1: Fundacion tecnica del backend

## Objetivo

Crear la base tecnica del backend. Esta fase no vende, no responde WhatsApp y no usa IA todavia. Su funcion es dejar el backend listo para crecer sin deuda tecnica inicial.

Esta fase es la mas importante arquitectonicamente. Si se hace mal, el resto del sistema se vuelve dificil de mantener: los workers quedan acoplados, la configuracion se duplica, los errores no son consistentes, los tests son fragiles y cada integracion empieza a resolver problemas de forma distinta.

## Resultado esperado

Al terminar esta fase debe existir un backend Django/DRF que:

- levanta localmente con un comando;
- tiene settings por entorno;
- conecta PostgreSQL;
- conecta Redis;
- ejecuta Celery;
- expone health checks reales;
- devuelve respuestas API consistentes;
- maneja errores de forma uniforme;
- tiene BaseModel comun;
- soporta soft delete;
- esta preparado para multi-tenant con `organization_id`;
- tiene idempotencia base;
- tiene outbox pattern;
- emite logs estructurados;
- expone OpenAPI;
- tiene tests base ejecutables.

## Modulos involucrados

- `config`
- `core`
- `integrations` basico
- `audit` basico

## Configuracion por entorno

La estructura objetivo de configuracion es:

```text
crm/config/
|-- settings/
|   |-- base.py
|   |-- local.py
|   |-- staging.py
|   |-- production.py
|   \-- test.py
|-- urls.py
|-- asgi.py
|-- wsgi.py
\-- celery.py
```

Cada entorno tiene un objetivo claro:

- `local`: desarrollo diario con `.env`;
- `test`: tests automaticos, base aislada, proveedores fake;
- `staging`: preproduccion, datos controlados, smoke tests;
- `production`: produccion real, secretos del entorno, seguridad estricta.

El codigo no debe depender de `.env` como requisito universal. `.env` es una comodidad local. Produccion debe usar variables/secrets del runtime.

## Variables minimas

```text
DJANGO_SETTINGS_MODULE
SECRET_KEY
DATABASE_URL
REDIS_URL
ALLOWED_HOSTS
CORS_ALLOWED_ORIGINS
CSRF_TRUSTED_ORIGINS
OPENAI_API_KEY
ANTHROPIC_API_KEY
WHATSAPP_ACCESS_TOKEN
WHATSAPP_VERIFY_TOKEN
WHATSAPP_APP_SECRET
S3_ENDPOINT_URL
S3_ACCESS_KEY_ID
S3_SECRET_ACCESS_KEY
S3_BUCKET_NAME
```

## Docker local

Debe existir un entorno local completo.

Servicios minimos:

- `api`: Django/DRF;
- `postgres`: PostgreSQL con pgvector;
- `redis`: broker/result backend;
- `worker`: Celery worker general;
- `scheduler`: Celery beat.

Comandos esperados:

```text
make dev
make migrate
make makemigrations
make shell
make test
make lint
make format
make createsuperuser
```

## Health checks

Endpoints obligatorios:

```text
GET /api/health/
GET /api/health/live/
GET /api/health/ready/
GET /api/version/
```

Diferencia:

- `live`: el proceso esta vivo;
- `ready`: el proceso puede operar porque DB, Redis y dependencias criticas responden;
- `version`: commit/build/version del backend.

`ready` no debe ser un "ok" falso. Debe consultar DB y Redis con timeout corto.

## Convencion de respuestas API

Respuesta exitosa:

```json
{
  "data": {},
  "meta": {
    "request_id": "..."
  }
}
```

Error:

```json
{
  "error": {
    "code": "resource_not_found",
    "message": "Resource not found",
    "details": {}
  },
  "meta": {
    "request_id": "..."
  }
}
```

Paginacion:

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 200,
    "has_next": true
  },
  "meta": {
    "request_id": "..."
  }
}
```

## BaseModel

Todos los modelos principales deben heredar de un modelo base.

Campos recomendados:

- `id`: UUID;
- `organization_id`: preparado para SaaS;
- `created_at`;
- `updated_at`;
- `deleted_at`: soft delete;
- `created_by_id`;
- `updated_by_id`;
- `metadata`: JSONB para datos flexibles.

Reglas:

- `metadata` no reemplaza campos importantes;
- `deleted_at` debe ser respetado por selectors;
- los models no deben contener workflows complejos;
- services hacen mutaciones;
- selectors encapsulan lecturas.

## Idempotencia

Debe existir una tabla:

```text
core_idempotency_key
```

Campos:

- `id`;
- `organization_id`;
- `key`;
- `scope`;
- `request_hash`;
- `response_body`;
- `status_code`;
- `status`;
- `expires_at`;
- `created_at`.

Uso esperado:

- requests HTTP mutables;
- webhooks de WhatsApp;
- jobs Celery reintentables;
- envios outbound;
- descargas de media;
- generacion IA.

## Outbox pattern

Debe existir:

```text
core_outbox_event
```

Campos:

- `id`;
- `organization_id`;
- `event_type`;
- `payload`;
- `status`;
- `attempts`;
- `available_at`;
- `locked_at`;
- `processed_at`;
- `error_message`;
- `created_at`.

Flujo:

```text
se guarda mensaje entrante
|
se guarda evento conversation.message_received.v1 en la misma transaccion
|
worker procesa evento despues
```

Esto evita perder logica si Redis, Celery o un worker caen despues de persistir el cambio de negocio.

## Logging estructurado

Todos los logs deben tener:

- `timestamp`;
- `level`;
- `environment`;
- `service`;
- `request_id`;
- `correlation_id`;
- `organization_id`;
- `user_id`;
- `event`;
- `message`;
- `metadata`.

No se deben loguear:

- tokens;
- API keys;
- passwords;
- access tokens de WhatsApp;
- payloads completos con datos sensibles;
- audios o transcripciones completas salvo en auditoria controlada.

## OpenAPI inicial

Endpoints esperados:

```text
GET /api/schema/
GET /api/docs/
```

El esquema sera usado por Next.js para generar tipos y cliente API. Desde esta fase debe existir la disciplina de contrato backend/frontend.

## Testing base

Setup requerido:

- `pytest`;
- `pytest-django`;
- factories;
- coverage;
- test database;
- settings fake;
- fake Redis o Redis de test;
- proveedores externos mockeados.

Tests minimos:

- `test_health_endpoint`;
- `test_ready_endpoint_with_db`;
- `test_error_response_format`;
- `test_pagination_format`;
- `test_base_model_fields`;
- `test_outbox_event_creation`;
- `test_idempotency_key_reuse`.

## Criterios de perfeccion

La fase 1 esta perfecta cuando:

1. El backend levanta localmente con un solo comando.
2. Hay settings separados por entorno.
3. Hay health checks reales.
4. Hay formato estandar de respuestas.
5. Hay formato estandar de errores.
6. Hay BaseModel reutilizable.
7. Hay idempotencia.
8. Hay outbox.
9. Hay Celery configurado.
10. Hay Redis configurado.
11. Hay PostgreSQL configurado.
12. Hay logging estructurado.
13. Hay OpenAPI inicial.
14. Hay tests base.
15. Ningun secreto esta hardcodeado.
16. El sistema puede desplegarse en staging sin reescribir configuracion.

## Riesgos a evitar

- meter logica de negocio en views;
- hacer health checks falsos;
- depender de `.env` en produccion;
- no tener request_id;
- crear modelos sin `organization_id`;
- usar Redis como fuente de verdad;
- lanzar jobs sin outbox;
- escribir tests que llaman proveedores reales.

## Recomendacion de division en subfases

### Fase 1.1: Layout tecnico

Entregables:

- estructura final de `config`;
- settings `base/local/test/staging/production`;
- `manage.py` apuntando al entorno local;
- `.env.example` completo;
- documentacion de variables.

Validacion:

- `python manage.py check`;
- `python manage.py diffsettings`;
- test que confirma el settings correcto.

### Fase 1.2: Docker y comandos

Entregables:

- `docker-compose.local.yml`;
- servicios `api`, `postgres`, `redis`, `worker`, `scheduler`;
- `Makefile` con comandos de desarrollo;
- volumes y health checks de contenedores.

Validacion:

- `make dev` levanta stack;
- `make migrate` corre migraciones;
- `make test` ejecuta tests.

### Fase 1.3: Core HTTP

Entregables:

- middleware `request_id`;
- response envelope;
- exception handler DRF;
- paginacion estandar;
- health endpoints;
- version endpoint.

Validacion:

- tests de formato de success/error/paginacion;
- tests de live/ready/version.

### Fase 1.4: Core persistencia

Entregables:

- `BaseModel`;
- soft delete;
- managers/selectors base;
- `IdempotencyKey`;
- `OutboxEvent`.

Validacion:

- tests de campos comunes;
- tests de idempotencia;
- tests de outbox en transaccion.

### Fase 1.5: Celery y outbox worker

Entregables:

- Celery configurado;
- beat configurado;
- worker de outbox;
- locking basico de eventos;
- retry con backoff.

Validacion:

- test de evento procesado;
- test de evento fallido;
- test de retry sin duplicar.

### Fase 1.6: OpenAPI y CI basico

Entregables:

- schema endpoint;
- docs endpoint;
- workflow CI;
- lint;
- format check;
- coverage inicial.

Validacion:

- CI verde;
- schema generado;
- frontend puede leer schema.
