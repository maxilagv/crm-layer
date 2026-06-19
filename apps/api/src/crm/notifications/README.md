# Notifications

## Objetivo

Modulo de notificaciones internas para owner/equipo: crear notificaciones, registrar deliveries,
respetar preferencias, quiet hours, rate limits, retries y digest diario.

## Modelos

- `Notification`: evento visible para el usuario.
- `NotificationDelivery`: intento de entrega por canal con status y errores sanitizados.
- `NotificationChannel`: configuracion de canal.
- `NotificationPreference`: preferencias por usuario/tipo/canal.
- `NotificationDigest`: resumen diario idempotente.

## Router y antispam

`NotificationRouter` siempre registra delivery dashboard y solo cola WhatsApp para prioridades
`high`/`urgent`. `NotificationRateLimiter` aplica:

- preferencias deshabilitadas;
- modo digest;
- quiet hours;
- maximo por hora.

Si se suprime un delivery, se emite `notification.suppressed.v1`.

## WhatsAppOwnerNotifier

No llama Meta directamente. Persiste `NotificationDelivery` y emite
`notification.owner_whatsapp_message.queued.v1` para que un adapter/gateway lo procese.

## Workers

- `notifications.send_notification`
- `notifications.retry_failed_delivery`
- `notifications.build_daily_digest`

## Endpoints

- `GET /api/v1/notifications/`
- `POST /api/v1/notifications/{id}/read/`
- `GET/PATCH /api/v1/notification-preferences/`

## Tests

Ver `tests/api/test_phase8_operations.py`.

