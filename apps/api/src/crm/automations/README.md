# Automations

## Objetivo

Motor de automatizaciones operativo: reglas por evento, conditions deterministicas, actions
autorizadas y runs/steps auditables.

## Modelos

- `AutomationRule`: regla tenant-scoped.
- `AutomationTrigger`: trigger normalizado de la regla.
- `AutomationCondition`: condicion evaluable sin `eval`.
- `AutomationAction`: accion con permiso requerido.
- `AutomationRun`: ejecucion idempotente por `rule + trigger_event_id`.
- `AutomationRunStep`: explicacion paso a paso de conditions/actions.

## Engine

`TriggerDispatcher` despacha reglas enabled y disabled. Las disabled producen run `skipped`,
lo que permite explicar por que no corrieron. `AutomationEngine` previene loops simples mediante
`source=automation` + `automation_depth`.

## Conditions

`ConditionEvaluator` usa operadores soportados: `eq`, `neq`, `gte`, `lte`, `gt`, `lt`,
`contains`, `in`. No usa `eval`.

## Actions

`ActionExecutor` soporta:

- `notify_owner` via `NotificationService`;
- `create_task` via `TaskCreator`;
- `update_lead_stage` via `lead_lifecycle.change_stage`;
- `create_ticket` via adapter explicito de support;
- `pause_ai` via `ConversationHandoffService`;
- `schedule_followup` via `sales.followup_service`;
- `send_whatsapp_message` solo si `policy_approved=true`, emitiendo outbox.

Cada action requiere permiso del creador de la regla, salvo reglas de sistema seed con
`system_allowed=true`.

## Workers

- `automations.dispatch_trigger`
- `automations.execute_rule`
- `automations.execute_action`

## Endpoints

- `GET/POST /api/v1/automations/rules/`
- `GET/PATCH /api/v1/automations/rules/{id}/`
- `POST /api/v1/automations/rules/{id}/enable/`
- `POST /api/v1/automations/rules/{id}/disable/`
- `GET /api/v1/automations/runs/`
- `GET /api/v1/automations/runs/{id}/`
- `POST /api/v1/automations/dispatch/`

## Tests

Ver `tests/api/test_phase8_operations.py`.

