# Alertas

Las alertas se definen en `AlertDefinition` y se materializan en `AlertEvent`.

Cada definicion tiene:

- `metric_name`
- `severity`
- `threshold_operator`
- `threshold_value`
- `window_minutes`
- `cooldown_minutes`
- `runbook_path`

Alertas default:

- WhatsApp webhook failing
- AI provider failing
- AI cost spike
- Failed messages spike

Las alertas no envian notificaciones por si mismas en Fase 9. Quedan persistidas y visibles para el panel; Fase 10 puede conectar canales de paging/notificacion.
