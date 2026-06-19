# Implementacion Fase 8

## Apps agregadas

- `crm.tasks`
- `crm.notifications`
- `crm.automations`

La ruta real del repo es `apps/api/src/crm/<app>`, por lo tanto no se uso
`crm/modules/...`.

## Decisiones tecnicas

- IA solo por `AIGateway.extract_tasks()`.
- No hay imports directos de OpenAI/Anthropic en Fase 8.
- Notificaciones WhatsApp del owner quedan como `NotificationDelivery` + outbox; no hay llamadas
  directas a Meta.
- Tareas, notificaciones y automation runs son tenant-scoped por `organization_id`.
- Conditions se evaluan con operadores deterministas, sin `eval`.
- Actions usan services/adapters de dominio existentes.
- `AutomationRun` y `AutomationRunStep` explican ejecuciones, skips y fallos.

## Integraciones

- `tasks` puede asociar `Contact`, `Lead`, `Client`, `SupportTicket` y `Conversation`.
- `TaskExtractor` consume output estructurado de Fase 5.
- `notifications` reemplaza adapters temporales futuros para hot leads/tickets.
- `automations` puede crear tareas, notificar owner, cambiar lead stage, crear ticket por adapter,
  pausar IA y schedule followup.

## Reparaciones de integracion

- Se agrego soporte OpenAPI explicito a actions sin body.
- Se corrigio `TicketLifecycleService.assign()` para que tickets `triaged` asignados pasen a
  `in_progress`, alineado con tests de Fase 7.
- Se dejo `support` con API/migracion existente validada por la suite.

## Validacion

- `manage.py check`: OK.
- `makemigrations --check --dry-run`: OK con SQLite temporal.
- `migrate`: OK con SQLite temporal.
- `pytest tests/api/test_phase8_operations.py -q`: 13 passed.
- `pytest tests/api/test_phase6_leads_sales.py -q`: 19 passed.
- `pytest -q` con SQLite temporal: 293 passed, 1 failed esperado por test que exige PostgreSQL.
- `ruff check .`: OK.
- `ruff format --check` sobre scope Fase 8: OK.
- `spectacular`: OpenAPI generado con `Errors: 0`, warnings de nombres de enums.

## Limites pendientes

- PostgreSQL local no valida por credenciales `ai_crm` rechazadas.
- `notification.owner_whatsapp_message.queued.v1` requiere handler/gateway outbound final.
- Fase 9 debe agregar metricas, auditoria avanzada, tracing, dashboards y evals operativas.

