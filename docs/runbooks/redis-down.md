# Redis Down

Severidad: critical

Senal:

- `/api/health/ready/` falla Redis;
- Celery no consume;
- rate limiting/cache fallan.

Acciones:

1. Verificar servicio Redis.
2. Revisar conectividad desde API y workers.
3. Confirmar `REDIS_URL`, `CELERY_BROKER_URL` y `CACHE_URL`.
4. Reiniciar workers despues de recuperar broker.
5. Revisar outbox para reprocesar eventos pendientes.
