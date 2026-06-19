# Fase 9: Analytics, auditoria, testing, evals y observabilidad

## Objetivo

Hacer que el backend sea medible, confiable y mantenible. Esta fase transforma el sistema de "funciona" a "puedo operarlo como producto serio".

Sin esta fase no sabes por que el bot respondio mal, cuanto gastaste en IA, que worker fallo, que lead se perdio o que webhook se duplico.

## Resultado esperado

Al terminar esta fase el backend debe poder:

- auditar cada evento critico;
- rastrear cada respuesta IA;
- medir costos IA;
- medir metricas comerciales;
- medir metricas tecnicas;
- exponer analytics para dashboard;
- ejecutar tests unitarios, integracion, API, workers y e2e;
- correr evals de IA;
- emitir logs estructurados con correlation_id;
- definir alertas operativas;
- diagnosticar fallos sin adivinar.

## Modulos involucrados

- `analytics`
- `audit`
- `ai.evals`
- `core.observability`
- todos los modulos

## Auditoria avanzada

Modelos:

- `audit_log`;
- `audit_data_access_log`;
- `audit_security_event`;
- `audit_ai_decision`;
- `audit_external_request`.

### AuditLog

Campos:

- `id`;
- `organization_id`;
- `actor_type`;
- `actor_id`;
- `action`;
- `resource_type`;
- `resource_id`;
- `before`;
- `after`;
- `ip_address`;
- `user_agent`;
- `request_id`;
- `created_at`.

Actor types:

- `user`;
- `ai_agent`;
- `system`;
- `webhook`;
- `worker`;
- `api_key`.

Acciones auditables:

- `user_login`;
- `contact_created`;
- `lead_updated`;
- `message_sent`;
- `ai_reply_generated`;
- `task_completed`;
- `ticket_resolved`;
- `prompt_activated`;
- `webhook_received`;
- `external_api_called`;
- `settings_updated`.

## Analytics

Modelos:

- `analytics_event`;
- `analytics_metric_snapshot`;
- `analytics_daily_summary`;
- `analytics_ai_cost_snapshot`;
- `analytics_funnel_snapshot`.

Metricas del CRM:

- `messages_received_total`;
- `messages_sent_total`;
- `leads_created_total`;
- `hot_leads_total`;
- `calls_requested_total`;
- `tickets_created_total`;
- `tasks_created_total`;
- `tasks_completed_total`;
- `average_response_time`;
- `ai_runs_total`;
- `ai_cost_total`;
- `whatsapp_failures_total`;
- `audio_transcription_failures_total`.

## Endpoints analytics

```text
GET /api/v1/analytics/dashboard/
GET /api/v1/analytics/leads/
GET /api/v1/analytics/conversations/
GET /api/v1/analytics/tasks/
GET /api/v1/analytics/tickets/
GET /api/v1/analytics/ai-costs/
GET /api/v1/analytics/whatsapp/
```

## Observabilidad

Cada request debe tener:

- `request_id`;
- `correlation_id`;
- `organization_id`;
- `user_id`.

Cada flujo importante debe propagar:

- `conversation_id`;
- `message_id`;
- `contact_id`;
- `lead_id`;
- `ticket_id`;
- `task_id`;
- `ai_run_id`.

Ejemplo de log:

```json
{
  "level": "info",
  "event": "sales.reply.generated",
  "organization_id": "...",
  "conversation_id": "...",
  "lead_id": "...",
  "ai_run_id": "...",
  "latency_ms": 1240,
  "cost_estimate": 0.0042
}
```

## Metricas tecnicas

- `http_requests_total`;
- `http_request_duration_seconds`;
- `celery_tasks_total`;
- `celery_task_failures_total`;
- `celery_queue_size`;
- `whatsapp_webhook_events_total`;
- `whatsapp_messages_sent_total`;
- `ai_runs_total`;
- `ai_failures_total`;
- `ai_cost_total`;
- `audio_transcriptions_total`;
- `tickets_created_total`;
- `tasks_created_total`;
- `notifications_sent_total`.

## Alertas

Alertas necesarias:

- WhatsApp webhook fallando;
- worker caido;
- cola creciendo;
- PostgreSQL sin espacio;
- Redis caido;
- OpenAI fallando;
- Anthropic fallando;
- costo IA anormal;
- muchos mensajes fallidos;
- backups fallando.

## Testing completo

Estructura:

```text
tests/
|-- unit/
|-- integration/
|-- api/
|-- workers/
|-- e2e/
|-- contracts/
|-- evals/
\-- factories/
```

### Tests unitarios

Deben probar reglas puras:

- lead scoring;
- conversation router;
- task command parser;
- notification rate limiter;
- support priority rules;
- sales policy.

### Tests de integracion

Deben probar modulos conectados:

- WhatsApp webhook a conversation message;
- message a sales agent a outbound message;
- audio a media a transcription a ticket;
- task reminder a WhatsApp owner notification.

### Tests API

Deben probar:

- auth;
- permissions;
- pagination;
- filters;
- CRUD;
- errors;
- OpenAPI schema.

### Tests de workers

Deben probar:

- idempotencia;
- retries;
- timeouts;
- errores externos;
- no duplicacion.

### Contract tests

Deben asegurar que Next.js pueda confiar en el esquema OpenAPI.

## Evals de IA

Datasets:

- `sales_conversations.yaml`;
- `support_audio_transcripts.yaml`;
- `task_extraction_cases.yaml`;
- `lead_scoring_cases.yaml`;
- `objection_handling_cases.yaml`;
- `handoff_cases.yaml`.

Metricas:

- `schema_validity`;
- `correct_intent`;
- `lead_score_error`;
- `task_extraction_precision`;
- `task_extraction_recall`;
- `handoff_accuracy`;
- `unsafe_reply_rate`;
- `sales_quality_score`;
- `support_quality_score`.

Casos obligatorios:

- lead pide precio y no hay politica: no inventar precio;
- cliente manda audio con bug: crear ticket;
- mensaje dice recordame manana: crear tarea;
- cliente enojado: derivar humano;
- lead quiere llamada: notificar owner;
- mensaje ambiguo: pedir aclaracion.

## Workers

- `analytics.collect_daily_metrics`;
- `analytics.build_dashboard_snapshot`;
- `analytics.calculate_ai_costs`;
- `audit.compact_old_logs`;
- `ai.run_eval_suite`;
- `observability.check_system_health`.

## Criterios de perfeccion

La fase 9 esta perfecta cuando:

1. Todo evento critico se audita.
2. Cada respuesta IA puede rastrearse.
3. Cada costo IA se mide.
4. Cada endpoint tiene tests.
5. Cada worker critico tiene tests.
6. Hay tests end-to-end.
7. Hay fake providers.
8. Hay evals de prompts.
9. Hay metricas comerciales.
10. Hay metricas tecnicas.
11. Hay logs estructurados.
12. Hay correlation_id en flujos.
13. Hay alertas definidas.
14. El dashboard puede mostrar metricas reales.
15. Un fallo puede diagnosticarse sin adivinar.

## Riesgos a evitar

- auditar solo algunos flujos;
- no propagar correlation_id a workers;
- medir costos IA de forma agregada sin contacto/conversacion;
- usar evals manuales sin datasets;
- tener tests que dependen de proveedores reales;
- no probar retries;
- no medir colas;
- no definir alertas antes de produccion.

## Recomendacion de division en subfases

### Fase 9.1: Auditoria avanzada

Entregables:

- AuditLog extendido;
- DataAccessLog;
- SecurityEvent;
- AIDecision;
- ExternalRequest.

Validacion:

- eventos criticos auditados;
- before/after guardado;
- filtros por recurso.

### Fase 9.2: Observabilidad tecnica

Entregables:

- request_id/correlation_id middleware;
- logging JSON;
- propagation a Celery;
- health worker.

Validacion:

- request_id aparece en logs;
- worker conserva correlation_id;
- fallo externo queda trazable.

### Fase 9.3: Analytics base

Entregables:

- AnalyticsEvent;
- snapshots diarios;
- dashboard endpoint;
- AI cost snapshots.

Validacion:

- metricas calculadas;
- costos por dia;
- dashboard responde.

### Fase 9.4: Testing por capas

Entregables:

- estructura tests;
- factories;
- fake providers;
- tests unit/integration/api/workers.

Validacion:

- suite completa corre local;
- coverage inicial aceptable;
- tests sin red externa.

### Fase 9.5: Evals IA

Entregables:

- datasets;
- eval runner;
- metricas;
- reportes persistidos.

Validacion:

- casos obligatorios pasan;
- unsafe replies detectadas;
- score de calidad visible.

### Fase 9.6: Alertas y runbooks

Entregables:

- alert definitions;
- thresholds;
- runbooks;
- checks periodicos.

Validacion:

- alerta simulada;
- runbook asociado;
- dashboard muestra estado.
