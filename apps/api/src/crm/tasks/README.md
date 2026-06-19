# Tasks

## Objetivo

Modulo operativo para tareas internas del CRM: tareas manuales, tareas extraidas por IA,
recordatorios, comandos del owner por WhatsApp, escalamiento e historial auditable.

## Modelos

- `Task`: unidad operativa con `organization_id`, estado, prioridad, origen, asociaciones y fecha.
- `TaskReminder`: recordatorio por canal, idempotente por tarea/canal/fecha.
- `TaskComment`: comentario interno.
- `TaskStatusHistory`: timeline de cambios de estado.
- `TaskCommand`: comando recibido desde WhatsApp y resultado de procesamiento.
- `TaskSource`: origen explicable de la tarea, incluido mensaje y `ai_run_id`.

## Lifecycle

Estados soportados: `pending`, `in_progress`, `waiting`, `completed`, `cancelled`,
`overdue`, `snoozed`.

Las mutaciones viven en services:

- `TaskCreator`
- `TaskUpdater`
- `TaskCompletionService`
- `TaskScheduler`
- `TaskReminderService`
- `TaskEscalationService`
- `TaskCommandParser`
- `TaskExtractor`

Cada cambio relevante emite outbox y registra audit cuando corresponde.

## Extraccion IA

`TaskExtractor` usa exclusivamente `AIGateway.extract_tasks()`. No llama proveedores directos
ni parsea texto libre para crear tareas. Solo crea tareas desde output estructurado validado por
Fase 5. Outputs ambiguos, de baja confianza o que requieren confirmacion se omiten.

## Deduplicacion

La deduplicacion cubre:

- `Task.idempotency_key`
- `TaskSource.organization_id + source_message + normalized_title`
- retries del worker de extraccion

## Recordatorios

`TaskScheduler` evita recordatorios pendientes duplicados. `TaskReminderService` no envia
recordatorios de tareas `completed` o `cancelled`; los expira. El envio pasa por
`NotificationService`.

## Comandos WhatsApp

El parser deterministico soporta `HECHO`, `PENDIENTE`, `POSPONER 2H`, `POSPONER 1D`,
`MANANA 10`, `CANCELAR` y `DETALLE`. Solo procesa mensajes de contactos marcados como owner
o vinculados al owner. Mensajes de clientes quedan rechazados y persistidos.

## Workers

- `tasks.extract_tasks_from_message`
- `tasks.send_due_reminders`
- `tasks.escalate_overdue_tasks`
- `tasks.parse_owner_command`

## Endpoints

- `GET/POST /api/v1/tasks/`
- `GET/PATCH /api/v1/tasks/{id}/`
- `POST /api/v1/tasks/{id}/complete/`
- `POST /api/v1/tasks/{id}/snooze/`
- `POST /api/v1/tasks/{id}/cancel/`
- `POST /api/v1/tasks/{id}/reminders/`

## Tests

Ver `tests/api/test_phase8_operations.py`.

