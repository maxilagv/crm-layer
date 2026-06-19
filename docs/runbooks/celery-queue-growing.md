# Celery Queue Growing

Severidad: high

Senal:

- colas `ai_fast`, `operations`, `notifications` o `analytics` creciendo.

Acciones:

1. Revisar Redis y workers activos.
2. Separar workers por cola critica.
3. Revisar tareas con retries repetidos.
4. Escalar workers temporalmente.
5. Inspeccionar `AuditExternalRequest` para errores de proveedor.
