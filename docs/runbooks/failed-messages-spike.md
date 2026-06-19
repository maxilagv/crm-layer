# Failed Messages Spike

Severidad: high

Senal:

- `failed_messages_total >= 10`.

Acciones:

1. Revisar `WhatsAppOutboundMessage.status=failed`.
2. Revisar error sanitizado en audit/external requests.
3. Confirmar que no haya rate limit o template rechazado.
4. Reintentar solo mensajes con idempotency key.
5. Informar manualmente al owner si el flujo comercial queda detenido.
