# Logging estructurado

El backend emite logs JSON mediante `crm.core.logging.JSONFormatter`.

Campos base:

- `timestamp`
- `level`
- `environment`
- `service`
- `request_id`
- `correlation_id`
- `organization_id`
- `user_id`
- `event`
- `message`
- `metadata`

Reglas:

- Los secrets se redactan por clave y por asignaciones tipo `token=...`.
- No se loguean payloads crudos de proveedores externos.
- Los errores externos se registran en `AuditExternalRequest`.
- Las tareas Celery restauran contexto desde headers `observability_context`.

Uso recomendado:

```python
from crm.core.observability.logging import log_event

log_event(logger, logging.INFO, "sales.reply.generated", "Sales reply generated", ai_run_id=run.id)
```
