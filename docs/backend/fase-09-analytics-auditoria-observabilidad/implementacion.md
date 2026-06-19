# Implementacion Fase 9

## Alcance

Se implemento la capa transversal de control operacional:

- auditoria avanzada;
- analytics durable;
- observabilidad con request/correlation id;
- propagacion de contexto Celery;
- eval datasets adicionales;
- alertas y runbooks.

## Decisiones

- `AuditEvent` se conserva por compatibilidad y se espeja a `AuditLog`.
- `AuditAIDecision` usa UUIDs sueltos para no acoplar audit con todos los dominios.
- Analytics calcula snapshots desde tablas reales, no desde valores hardcodeados.
- `MetricsRecorder` es tecnico y process-local; no reemplaza snapshots durables.
- Las alertas se persisten, pero la notificacion/paging queda para Fase 10.

## Endpoints

- `GET /api/v1/analytics/dashboard/`
- `GET /api/v1/analytics/leads/`
- `GET /api/v1/analytics/conversations/`
- `GET /api/v1/analytics/tasks/`
- `GET /api/v1/analytics/tickets/`
- `GET /api/v1/analytics/ai-costs/`
- `GET /api/v1/analytics/whatsapp/`
- `GET /api/v1/audit/logs/`
- `GET /api/v1/audit/data-access/`
- `GET /api/v1/audit/security-events/`
- `GET /api/v1/audit/ai-decisions/`
- `GET /api/v1/audit/external-requests/`
- `GET /api/system/status/`

## Workers

- `analytics.collect_daily_metrics`
- `analytics.build_dashboard_snapshot`
- `analytics.calculate_ai_costs`
- `analytics.check_alerts`
- `audit.compact_old_logs`
- `observability.check_system_health`

## Validacion esperada

```bash
python apps/api/manage.py check --settings=crm.config.settings.test
python apps/api/manage.py migrate --settings=crm.config.settings.test
cd apps/api && pytest tests/unit/test_phase9_audit_observability.py tests/workers/test_phase9_analytics_workers.py tests/api/test_phase9_analytics_audit_api.py tests/evals/test_phase9_eval_datasets.py tests/contracts/test_phase9_openapi.py -q
```
