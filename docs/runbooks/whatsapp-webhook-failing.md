# WhatsApp Webhook Failing

Severidad: high

Senal:

- `whatsapp_failures_total >= 5`
- eventos `webhook_signature_invalid`
- errores recientes en `AuditExternalRequest` con provider `whatsapp`

Acciones:

1. Revisar `/api/health/ready/`.
2. Confirmar `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN` y URL publica.
3. Revisar eventos en `/api/v1/audit/security-events/`.
4. Revisar dead letters de outbox en `/api/system/status/`.
5. Reprocesar eventos solo si son idempotentes.
