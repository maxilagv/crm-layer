# Metricas

La Fase 9 separa dos tipos de metricas:

- metricas durables de negocio en `crm.analytics`;
- contadores tecnicos locales en `MetricsRecorder`.

Snapshots durables:

- `AnalyticsDailySummary`
- `AnalyticsMetricSnapshot`
- `AnalyticsAICostSnapshot`
- `AnalyticsFunnelSnapshot`
- `AnalyticsDashboardSnapshot`

Comandos:

```bash
python apps/api/manage.py analytics_collect_daily_metrics --organization-id <uuid>
python apps/api/manage.py analytics_calculate_ai_costs --organization-id <uuid>
python apps/api/manage.py analytics_build_dashboard_snapshot --organization-id <uuid>
python apps/api/manage.py analytics_check_alerts --organization-id <uuid>
```

Las metricas se calculan desde tablas reales: mensajes, leads, tickets, tareas, notificaciones, automatizaciones y `AIUsageRecord`.
