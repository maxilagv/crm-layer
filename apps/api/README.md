# AI CRM API

Backend Django/DRF del CRM. Fase 1: fundación técnica (settings por entorno,
health checks reales, envelope de respuestas, BaseModel con soft delete,
idempotencia, outbox pattern, Celery, logging estructurado y OpenAPI).

## Layout

```text
apps/api/
|-- manage.py
|-- pyproject.toml
|-- src/crm/
|   |-- config/            # settings por entorno, urls, celery, asgi/wsgi
|   |   \-- settings/      # base, local, test, staging, production
|   |-- core/              # infraestructura transversal
|   |   |-- api/           # health, envelope, exception handler, paginacion
|   |   |-- services/      # idempotency, outbox (mutaciones)
|   |   |-- selectors/     # lecturas encapsuladas
|   |   |-- middleware.py  # request_id / correlation_id
|   |   |-- logging.py     # JSON formatter + redaccion de secretos
|   |   \-- models.py      # BaseModel, IdempotencyKey, OutboxEvent
|   |-- integrations/      # base para proveedores externos (fases futuras)
|   \-- audit/             # base de auditoria (fases futuras)
\-- tests/
```

## Settings por entorno

`DJANGO_SETTINGS_MODULE` selecciona el entorno:

- `crm.config.settings.local`: desarrollo diario; carga `.env` del repo como comodidad.
- `crm.config.settings.test`: pytest; PostgreSQL de test, fakeredis, Celery eager, proveedores vacíos.
- `crm.config.settings.staging`: preproducción; requiere `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` desde el runtime.
- `crm.config.settings.production`: igual que staging más HSTS completo. Nunca lee `.env`.

Variables soportadas: ver [.env.example](../../.env.example). `.env` es solo
una comodidad local.

## Desarrollo local

Desde la raíz del repo:

```bash
cp .env.example .env
make dev        # api + web + postgres(pgvector) + redis + worker + scheduler
make migrate
make createsuperuser
```

## Health endpoints

- `GET /api/health/` — agregado simple, sin tocar dependencias.
- `GET /api/health/live/` — proceso vivo; nunca consulta DB/Redis.
- `GET /api/health/ready/` — consulta PostgreSQL y Redis con timeout corto; 503 con error envelope si algo falla.
- `GET /api/version/` — `APP_VERSION`, `GIT_COMMIT`, `BUILD_DATE`, entorno.

## Convención de respuestas

```json
{"data": {...}, "meta": {"request_id": "..."}}
{"error": {"code": "...", "message": "...", "details": {}}, "meta": {"request_id": "..."}}
{"data": [...], "pagination": {"page": 1, "page_size": 50, "total": 200, "has_next": true}, "meta": {"request_id": "..."}}
```

Implementado en `crm.core.api` (responses, exceptions, pagination). Las views
no construyen JSON a mano.

## Tests

Con Docker (recomendado):

```bash
make test
```

Sin Docker se necesita un PostgreSQL accesible (los tests usan una base
`test_*` propia):

```bash
cd apps/api
pip install -e ".[dev]"
set DATABASE_URL=postgres://user:pass@localhost:5432/ai_crm
pytest --cov=crm
```

Ningún test llama proveedores reales (OpenAI/Anthropic/WhatsApp/S3).

## OpenAPI

- `GET /api/schema/` — schema para generar tipos/cliente en Next.js.
- `GET /api/docs/` — Swagger UI local.

## Patrones core

- **BaseModel**: UUID pk, `organization_id` (multi-tenant desde el día 1),
  timestamps, soft delete con managers (`objects` excluye borrados,
  `all_objects` incluye), `metadata` JSONB.
- **Idempotencia** (`crm.core.services.idempotency`): `start/complete/fail`
  bajo row lock, conflicto por `request_hash`, TTL con expiración.
- **Outbox** (`crm.core.services.outbox`): evento persistido en la misma
  transacción que el cambio de negocio; worker Celery con `SKIP LOCKED`,
  retry con backoff, dead letter y requeue de locks huérfanos. Los handlers
  se registran con `@register_outbox_handler("tipo.de.evento.v1")`.
