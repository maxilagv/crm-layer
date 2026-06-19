.DEFAULT_GOAL := help

COMPOSE := docker compose -f docker-compose.local.yml
PROD_COMPOSE := docker compose --env-file .env.prod -f docker-compose.prod.yml

.PHONY: help
help:
	@printf "AI CRM commands\n"
	@printf "  make dev             Start local stack (api, web, postgres, redis, worker, scheduler)\n"
	@printf "  make down            Stop local stack\n"
	@printf "  make logs            Tail local logs\n"
	@printf "  make migrate         Run Django migrations\n"
	@printf "  make quickstart      One-command setup (owner+org, Gemini, prompts, profile)\n"
	@printf "  make makemigrations  Create Django migrations\n"
	@printf "  make shell           Open Django shell\n"
	@printf "  make createsuperuser Create Django superuser\n"
	@printf "  make test            Run backend tests with coverage\n"
	@printf "  make lint            Run linters (ruff + format check, pnpm lint)\n"
	@printf "  make format          Format Python and TypeScript code\n"
	@printf "  make check           Run Django system checks and migration drift check\n"
	@printf "  make ci              Run backend checks, pytest, and frontend build\n"
	@printf "  make prod-up         Build and start production stack\n"
	@printf "  make prod-down       Stop production stack\n"
	@printf "  make prod-logs       Tail production logs\n"
	@printf "  make prod-migrate    Run production migrations\n"
	@printf "  make backup          Create a production Postgres backup now\n"
	@printf "  make restore FILE=/backups/postgres-...sql.gz  Restore a backup\n"

.PHONY: dev
dev:
	$(COMPOSE) up --build

.PHONY: down
down:
	$(COMPOSE) down

.PHONY: logs
logs:
	$(COMPOSE) logs -f --tail=200

.PHONY: migrate
migrate:
	$(COMPOSE) run --rm api python manage.py migrate

.PHONY: makemigrations
makemigrations:
	$(COMPOSE) run --rm api python manage.py makemigrations

# One-command bootstrap. Override the vars, e.g.:
#   make quickstart EMAIL=yo@ejemplo.com NAME="Maxi" ORG="Mi Estudio" PASSWORD=secret PHONE=5491137725766
EMAIL ?= owner@example.com
NAME ?= Owner
ORG ?= Mi Estudio
PASSWORD ?=
PHONE ?=
GEMINI_MODEL ?= gemini-2.5-flash

.PHONY: quickstart
quickstart:
	$(COMPOSE) run --rm api python manage.py quickstart \
		--email "$(EMAIL)" --name "$(NAME)" --organization "$(ORG)" \
		--password "$(PASSWORD)" --owner-phone "$(PHONE)" --gemini-model "$(GEMINI_MODEL)"

.PHONY: shell
shell:
	$(COMPOSE) run --rm api python manage.py shell

.PHONY: createsuperuser
createsuperuser:
	$(COMPOSE) run --rm api python manage.py createsuperuser

.PHONY: test
test:
	$(COMPOSE) run --rm api pytest --cov=crm --cov-report=term-missing

.PHONY: lint
lint:
	pnpm lint
	$(COMPOSE) run --rm api ruff check .
	$(COMPOSE) run --rm api ruff format --check .

.PHONY: format
format:
	pnpm format
	$(COMPOSE) run --rm api ruff format .
	$(COMPOSE) run --rm api ruff check --fix .

.PHONY: check
check:
	$(COMPOSE) run --rm api python manage.py check
	$(COMPOSE) run --rm api python manage.py makemigrations --check --dry-run

.PHONY: ci
ci:
	pnpm lint
	pnpm --filter @ai-crm/web build
	$(COMPOSE) run --rm api ruff check src tests
	$(COMPOSE) run --rm api ruff format --check src tests
	$(COMPOSE) run --rm api python manage.py makemigrations --check --dry-run
	$(COMPOSE) run --rm \
		-e DJANGO_SETTINGS_MODULE=crm.config.settings.prod \
		-e DEBUG=false \
		-e SECRET_KEY=ci-secret-key-with-more-than-fifty-characters-for-deploy-checks \
		-e JWT_SIGNING_KEY=ci-jwt-signing-key-with-more-than-thirty-two-bytes \
		-e WA_BRIDGE_SHARED_SECRET=ci-wa-bridge-secret-with-more-than-thirty-two-bytes \
		-e DATABASE_URL=postgres://ai_crm:ai_crm@postgres:5432/ai_crm \
		-e REDIS_URL=redis://redis:6379/0 \
		-e ALLOWED_HOSTS=example.com \
		-e CORS_ALLOWED_ORIGINS=https://example.com \
		-e CSRF_TRUSTED_ORIGINS=https://example.com \
		api python manage.py check --deploy
	$(COMPOSE) run --rm api pytest --reuse-db -p no:cacheprovider -q

.PHONY: prod-up
prod-up:
	$(PROD_COMPOSE) up -d --build

.PHONY: prod-down
prod-down:
	$(PROD_COMPOSE) down

.PHONY: prod-logs
prod-logs:
	$(PROD_COMPOSE) logs -f --tail=200

.PHONY: prod-migrate
prod-migrate:
	$(PROD_COMPOSE) run --rm api python manage.py migrate

.PHONY: backup
backup:
	$(PROD_COMPOSE) run --rm backup /scripts/postgres-backup.sh

.PHONY: restore
restore:
	@test -n "$(FILE)" || (echo "Set FILE=/backups/postgres-YYYYmmddTHHMMSSZ.sql.gz" && exit 2)
	$(PROD_COMPOSE) run --rm backup /scripts/postgres-restore.sh "$(FILE)"
