# Worker Down

Severidad: critical

Senal:

- tareas sin procesar;
- outbox en `processing` stale;
- system status degradado.

Acciones:

1. Verificar proceso Celery.
2. Verificar Redis.
3. Revisar `celery.task_failed` en logs.
4. Reiniciar worker si no hay tareas activas criticas.
5. Validar que `correlation_id` aparezca en los logs posteriores.
