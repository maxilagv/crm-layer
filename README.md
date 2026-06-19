# AI CRM

CRM operativo privado orientado a WhatsApp, ventas consultivas, soporte, tareas y asistencia con IA.

## Objetivo

El sistema separa responsabilidades de forma estricta:

- `apps/api`: backend Django/DRF, webhooks, reglas de negocio, workers Celery, IA, scoring, tickets, tareas, auditoria y persistencia.
- `apps/web`: panel Next.js para inbox, leads, clientes, tickets, tareas, prompts, metricas y control manual.
- `packages/contracts`: contratos compartidos entre frontend y backend.
- `infra`: Docker, Caddy, base de datos, backups, despliegue y monitoreo.
- `docs`: decisiones de producto, arquitectura, ADRs, runbooks, seguridad y prompts.

## Horizonte actual

Estamos en Horizonte 0: cerrar arquitectura, dominio, limites de sistema y estructura base. La implementacion funcional empieza desde Horizonte 1 con WhatsApp, conversaciones, contactos, clasificador lead/cliente y admin simple.

## Desarrollo local

1. Copiar `.env.example` a `.env` y completar secretos.
2. Instalar dependencias JS con `pnpm install`.
3. Levantar servicios con `make dev`.
4. Ejecutar migraciones con `make migrate`.
5. Dejar la instancia usable en un solo paso con `make quickstart` (crea owner + organizacion, configura Gemini, siembra los prompts y completa el perfil de negocio):

   ```
   make quickstart EMAIL=yo@ejemplo.com NAME="Maxi" ORG="Mi Estudio" \
       PASSWORD=secreto PHONE=5491137725766
   ```

   Despues entra al panel (http://localhost:3000), modulo Tareas, y carga recordatorios. Para WhatsApp conecta el numero por QR en Config > WhatsApp.

## Puertos locales

- Web: http://localhost:3000
- API: http://localhost:8000
- Admin Django: http://localhost:8000/admin

## Documentacion clave

- [Arquitectura del sistema](docs/architecture/system-context.md)
- [Backend por fases](docs/backend/README.md)
- [Limites de modulos](docs/architecture/module-boundaries.md)
- [Modelo de datos inicial](docs/architecture/data-model.md)
- [Horizontes de producto](docs/product/horizons.md)
- [Decisiones de Horizonte 0](docs/product/horizon-0-decisions.md)
- [Runbook local](docs/runbooks/local-dev.md)
