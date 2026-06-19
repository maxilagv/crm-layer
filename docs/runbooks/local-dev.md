# Runbook local

## Preparacion

```bash
cp .env.example .env
pnpm install
cd apps/api && python -m pip install -e ".[dev]"
docker compose -f docker-compose.local.yml build
```

`.env` es solo comodidad local. Staging y produccion deben recibir secrets desde el runtime.

## Levantar stack

```bash
make dev
```

## Migraciones

```bash
make migrate
```

Sin Docker, solo para validar settings/test database:

```bash
cd apps/api
python manage.py migrate --settings=crm.config.settings.test --noinput
```

## Quickstart (instancia usable en un paso)

Despues de `make dev` + `make migrate`, deja la instancia lista (owner + organizacion,
proveedor Gemini, prompts versionados y perfil de negocio con telefono del owner) con:

```bash
make quickstart EMAIL=yo@ejemplo.com NAME="Maxi" ORG="Mi Estudio" \
    PASSWORD=secreto PHONE=5491137725766
```

Variables: `EMAIL`, `NAME`, `ORG`, `PASSWORD`, `PHONE` (telefono E.164 del owner para
recordatorios y notificaciones por WhatsApp) y `GEMINI_MODEL` (default `gemini-2.5-flash`).
Es idempotente: re-ejecutarlo no duplica la organizacion ni los prompts.

Equivalente sin `make`:

```bash
docker compose -f docker-compose.local.yml run --rm api \
    python manage.py quickstart --email yo@ejemplo.com --name "Maxi" \
    --organization "Mi Estudio" --owner-phone 5491137725766
```

Para que los recordatorios lleguen por WhatsApp ademas hace falta: definir
`OWNER_WHATSAPP_NUMBER` en `.env`, tener el worker con todas las colas (`-Q ...`,
ya incluido en compose) y vincular el numero por QR en Config > WhatsApp.

## Admin Django

```bash
make createsuperuser
```

Abrir `http://localhost:8000/admin`.

## Healthcheck

```bash
curl http://localhost:8000/api/health/
curl http://localhost:8000/api/health/live/
curl http://localhost:8000/api/health/ready/
curl http://localhost:8000/api/version/
```

## OpenAPI

```bash
curl http://localhost:8000/api/schema/
```

Docs locales: `http://localhost:8000/api/docs/`.

## Tests y calidad

```bash
make test     # pytest + coverage (corre dentro del contenedor api)
make lint     # ruff check + ruff format --check + pnpm lint
make format   # ruff format + ruff check --fix + pnpm format
make check    # manage.py check + makemigrations --check
```

Los tests corren contra PostgreSQL real (base `test_*` descartable), fakeredis
y Celery en modo eager. Ningún test llama proveedores externos.

## Apagar el stack

```bash
make down
```

## Tests y calidad

```bash
make test
make lint
make format
```

Equivalentes sin `make`:

```bash
pnpm lint
pnpm typecheck
cd apps/api
ruff check .
pytest
```
