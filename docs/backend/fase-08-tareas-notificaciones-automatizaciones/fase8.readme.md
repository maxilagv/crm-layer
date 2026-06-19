# Fase 8: Tareas, recordatorios, notificaciones y automatizaciones

> Implementacion backend: ver `implementacion.md`.

## Objetivo

Convertir el CRM en un sistema operativo personal. El backend no solo conversa: detecta tareas, las manda por WhatsApp, espera comandos, recuerda, escala y automatiza flujos.

Esta fase crea el asistente operativo.

## Resultado esperado

Al terminar esta fase el backend debe poder:

- crear tareas manuales;
- extraer tareas desde conversaciones;
- asociar tareas a leads, clientes, tickets y conversaciones;
- programar recordatorios;
- enviar notificaciones al owner;
- interpretar comandos por WhatsApp;
- completar, posponer o cancelar tareas desde mensajes;
- escalar tareas vencidas;
- evitar spam interno;
- ejecutar automatizaciones basadas en eventos;
- registrar cada automation run.

## Modulos involucrados

- `tasks`
- `notifications`
- `automations`
- `ai`
- `conversations`
- `whatsapp`
- `contacts`
- `leads`
- `clients`
- `support`
- `audit`
- `settings`

## Modelos de tareas

Modelos esperados:

- `tasks_task`;
- `tasks_task_reminder`;
- `tasks_task_comment`;
- `tasks_task_status_history`;
- `tasks_task_command`;
- `tasks_task_source`.

### Task

Campos:

- `id`;
- `organization_id`;
- `title`;
- `description`;
- `status`;
- `priority`;
- `source_type`;
- `source_id`;
- `contact_id`;
- `lead_id`;
- `client_id`;
- `ticket_id`;
- `conversation_id`;
- `assigned_to_id`;
- `due_at`;
- `completed_at`;
- `metadata`;
- `created_at`;
- `updated_at`.

Estados:

- `pending`;
- `in_progress`;
- `waiting`;
- `completed`;
- `cancelled`;
- `overdue`;
- `snoozed`.

Prioridades:

- `low`;
- `medium`;
- `high`;
- `urgent`.

Sources:

- `manual`;
- `conversation`;
- `lead`;
- `ticket`;
- `ai_extracted`;
- `automation`;
- `system`.

### TaskReminder

Campos:

- `id`;
- `organization_id`;
- `task_id`;
- `remind_at`;
- `channel`;
- `status`;
- `sent_at`;
- `acknowledged_at`;
- `snoozed_until`;
- `metadata`;
- `created_at`.

Canales:

- `whatsapp`;
- `dashboard`;
- `email`;
- `system`.

### TaskCommand

Campos:

- `id`;
- `organization_id`;
- `task_id`;
- `message_id`;
- `raw_command`;
- `parsed_command`;
- `status`;
- `result`;
- `created_at`.

Comandos soportados:

- `HECHO`;
- `PENDIENTE`;
- `POSPONER 2H`;
- `POSPONER 1D`;
- `MANANA 10`;
- `CANCELAR`;
- `DETALLE`.

## Modelos de notificaciones

Modelos esperados:

- `notifications_notification`;
- `notifications_delivery`;
- `notifications_channel`;
- `notifications_preference`;
- `notifications_digest`.

### Notification

Campos:

- `id`;
- `organization_id`;
- `recipient_user_id`;
- `type`;
- `title`;
- `body`;
- `priority`;
- `status`;
- `resource_type`;
- `resource_id`;
- `metadata`;
- `created_at`.

Tipos:

- `hot_lead`;
- `call_requested`;
- `urgent_ticket`;
- `task_due`;
- `task_overdue`;
- `ai_failure`;
- `whatsapp_failure`;
- `system_alert`;
- `daily_digest`.

## Modelos de automatizaciones

Modelos esperados:

- `automations_rule`;
- `automations_trigger`;
- `automations_condition`;
- `automations_action`;
- `automations_run`;
- `automations_run_step`.

### AutomationRule

Campos:

- `id`;
- `organization_id`;
- `name`;
- `description`;
- `trigger_type`;
- `conditions`;
- `actions`;
- `is_enabled`;
- `priority`;
- `created_by_id`;
- `metadata`;
- `created_at`;
- `updated_at`.

Triggers:

- `message_received`;
- `lead_score_changed`;
- `lead_became_hot`;
- `ticket_created`;
- `task_due`;
- `task_overdue`;
- `audio_transcribed`;
- `client_registered`;
- `conversation_paused`.

Actions:

- `send_whatsapp_message`;
- `notify_owner`;
- `create_task`;
- `update_lead_stage`;
- `create_ticket`;
- `pause_ai`;
- `assign_user`;
- `schedule_followup`.

## Servicios

Servicios esperados:

- `TaskExtractor`;
- `TaskCreator`;
- `TaskScheduler`;
- `TaskReminderService`;
- `TaskCommandParser`;
- `TaskCompletionService`;
- `TaskEscalationService`;
- `NotificationService`;
- `NotificationRouter`;
- `WhatsAppOwnerNotifier`;
- `DigestBuilder`;
- `DeliveryRetryService`;
- `AutomationEngine`;
- `TriggerDispatcher`;
- `ConditionEvaluator`;
- `ActionExecutor`;
- `AutomationRunLogger`.

## Flujo de extraccion de tarea

```text
mensaje entrante
|
AI task extractor analiza
|
detecta compromiso o accion
|
crea task candidate
|
valida duplicados
|
crea task
|
programa reminder
|
notifica si corresponde
```

Ejemplo:

```text
Manana le paso presupuesto a Juan.
```

Output:

```json
{
  "tasks": [
    {
      "title": "Enviar presupuesto a Juan",
      "due_at": "2026-06-12T10:00:00-03:00",
      "priority": "high",
      "source": "conversation",
      "confidence": 0.91
    }
  ]
}
```

## Flujo de recordatorio por WhatsApp

```text
scheduler detecta tarea vencida o proxima
|
NotificationService crea notificacion
|
WhatsAppOwnerNotifier envia mensaje al numero del owner
|
owner responde HECHO / PENDIENTE / POSPONER
|
TaskCommandParser interpreta
|
TaskCompletionService actualiza estado
|
se audita accion
```

Mensaje ideal:

```text
Tarea pendiente: llamar a Juan por automatizacion de WhatsApp.
Vence: hoy 16:00.
Responder: HECHO, PENDIENTE, POSPONER 2H o CANCELAR.
```

## Antispam interno

El sistema no debe molestar todo el tiempo.

Reglas:

- agrupar tareas de baja prioridad;
- notificar inmediato solo high/urgent;
- no repetir mas de X veces por hora;
- escalar si esta muy vencida;
- permitir modo silencio;
- crear resumen diario.

## Automatizaciones iniciales recomendadas

1. Si `lead_score >= 80`, notificar owner y crear tarea de llamada.
2. Si `ticket.priority == urgent`, notificar owner inmediato.
3. Si una tarea vence en 30 minutos, mandar recordatorio.
4. Si cliente manda audio, crear ticket.
5. Si conversacion pasa a manual, pausar IA.
6. Si lead no responde en 48 horas, crear follow-up.

## Endpoints

```text
GET   /api/v1/tasks/
POST  /api/v1/tasks/
GET   /api/v1/tasks/{id}/
PATCH /api/v1/tasks/{id}/

POST  /api/v1/tasks/{id}/complete/
POST  /api/v1/tasks/{id}/snooze/
POST  /api/v1/tasks/{id}/cancel/
POST  /api/v1/tasks/{id}/reminders/

GET   /api/v1/notifications/
POST  /api/v1/notifications/{id}/read/
GET   /api/v1/notification-preferences/
PATCH /api/v1/notification-preferences/

GET   /api/v1/automations/rules/
POST  /api/v1/automations/rules/
GET   /api/v1/automations/rules/{id}/
PATCH /api/v1/automations/rules/{id}/
POST  /api/v1/automations/rules/{id}/enable/
POST  /api/v1/automations/rules/{id}/disable/
```

## Workers

- `tasks.extract_tasks_from_message`;
- `tasks.send_due_reminders`;
- `tasks.escalate_overdue_tasks`;
- `tasks.parse_owner_command`;
- `notifications.send_notification`;
- `notifications.retry_failed_delivery`;
- `notifications.build_daily_digest`;
- `automations.dispatch_trigger`;
- `automations.execute_rule`;
- `automations.execute_action`.

## Tests obligatorios

- `test_task_created_manually`;
- `test_task_extracted_from_message`;
- `test_duplicate_task_prevented`;
- `test_due_task_sends_reminder`;
- `test_owner_command_hecho_completes_task`;
- `test_owner_command_posponer_snoozes_task`;
- `test_overdue_task_escalates`;
- `test_hot_lead_automation_creates_task`;
- `test_urgent_ticket_automation_notifies`;
- `test_notification_rate_limit`.

## Criterios de perfeccion

La fase 8 esta perfecta cuando:

1. Las tareas pueden crearse manualmente.
2. Las tareas pueden extraerse de conversaciones.
3. Las tareas tienen fecha, prioridad y origen.
4. Los recordatorios funcionan.
5. Las respuestas por WhatsApp actualizan tareas.
6. Los comandos se interpretan correctamente.
7. Las tareas vencidas escalan.
8. Las notificaciones no hacen spam.
9. Los eventos importantes notifican.
10. Las automatizaciones tienen triggers.
11. Las automatizaciones tienen condiciones.
12. Las automatizaciones tienen acciones.
13. Cada automation run queda registrado.
14. Todo es idempotente.
15. Hay tests completos de flujo.

## Riesgos a evitar

- crear tareas duplicadas desde el mismo mensaje;
- notificar demasiado;
- ejecutar automatizaciones sin logging;
- permitir actions sin permisos;
- posponer tareas sin limite;
- bloquear workers de WhatsApp con automatizaciones lentas;
- interpretar comandos del cliente como comandos del owner.

## Recomendacion de division en subfases

### Fase 8.1: Modelo de tareas

Entregables:

- Task;
- TaskReminder;
- TaskStatusHistory;
- endpoints CRUD;
- filtros por estado/due_at/prioridad.

Validacion:

- creacion manual;
- cambio de estado;
- historial.

### Fase 8.2: Extraccion IA de tareas

Entregables:

- TaskExtractor;
- schema de task candidate;
- deduplicacion;
- asociacion con message/conversation/contact.

Validacion:

- mensaje con compromiso crea tarea;
- mensaje ambiguo no crea;
- duplicado prevenido.

### Fase 8.3: Recordatorios

Entregables:

- scheduler;
- send_due_reminders;
- reminder status;
- rate limit.

Validacion:

- tarea por vencer notifica;
- baja prioridad se agrupa;
- no repite demasiado.

### Fase 8.4: Comandos por WhatsApp

Entregables:

- TaskCommand;
- parser deterministico;
- parser IA opcional para frases naturales;
- complete/snooze/cancel.

Validacion:

- HECHO completa;
- POSPONER 2H cambia due_at;
- comando invalido pide aclaracion.

### Fase 8.5: Notificaciones

Entregables:

- Notification;
- Delivery;
- NotificationRouter;
- WhatsAppOwnerNotifier;
- DailyDigest.

Validacion:

- hot lead notifica;
- urgent ticket notifica;
- digest se genera.

### Fase 8.6: Automation engine

Entregables:

- AutomationRule;
- TriggerDispatcher;
- ConditionEvaluator;
- ActionExecutor;
- AutomationRun;
- AutomationRunStep.

Validacion:

- regla enabled ejecuta;
- regla disabled no ejecuta;
- run queda registrado;
- action fallida queda visible.
