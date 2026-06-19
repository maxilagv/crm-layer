# ADR 0002: Python controla workflows criticos

## Estado

Aceptado.

## Decision

Django y Celery reciben webhooks, procesan audios, ejecutan scoring, coordinan IA, crean tareas y envian WhatsApp. Next.js solo consume APIs y opera el panel.

## Motivo

Los flujos criticos necesitan persistencia, colas, reintentos, auditoria y reglas de negocio centralizadas.

## Consecuencias

- Los endpoints de WhatsApp viven en `apps/api`.
- Next.js no puede enviar mensajes proactivos directamente.
- Las acciones manuales del panel deben pasar por la API.
