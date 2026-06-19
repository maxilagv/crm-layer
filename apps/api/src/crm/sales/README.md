# Sales

Motor de agente vendedor, oportunidades, objeciones, followups y solicitudes de
llamada.

## Objetivo

`crm.sales` genera respuestas comerciales seguras, maneja objeciones, crea
solicitudes de llamada, crea followups y mantiene oportunidades.

## Modelos

- `SalesOpportunity`: oportunidad comercial vinculada a un lead.
- `SalesFollowup`: tarea comercial idempotente hasta que exista el modulo global
  de tareas.
- `SalesObjection`: objeciones detectadas por mensaje/tipo.
- `SalesPlaybook`: playbooks comerciales versionables por organizacion.
- `SalesCallRequest`: solicitud de llamada con estados operativos.

## Agente Vendedor

`SalesConversationAgent` usa:

1. `LeadCreationService` para crear/reusar lead.
2. `LeadScoringService` para recalcular score.
3. `AIGateway.generate_sales_reply()` para respuesta estructurada.
4. `SafetyGuard` integrado en `AIGateway`.
5. `SalesReplyPolicy` para guardrails comerciales deterministas.
6. Outbox `sales.reply_ready.v1` para que una capa de envio procese la respuesta.

Sales no llama Meta API, OpenAI ni Anthropic.

## Guardrails

`SalesReplyPolicy` bloquea respuestas que:

- mencionan precios sin `SalesPolicy.can_quote_prices`;
- prometen resultados garantizados;
- inventan disponibilidad;
- usan lenguaje agresivo;
- mencionan casos de exito no configurados;
- solicitan datos sensibles;
- intentan cerrar contrato o pago sin humano;
- ignoran objeciones explicitas de precio.

## Objeciones

`SalesObjectionHandler` detecta precio, tiempo y falta de interes. La
deduplicacion ocurre por `organization_id + lead + objection_type + message`.

## Call Requests

`SalesCallRequest` no permite mas de una solicitud abierta por lead. Los estados
abiertos son `requested`, `owner_notified` y `scheduled`.

## Followups

`SalesFollowup` usa `idempotency_key`. En esta fase funciona como tarea
comercial propia; cuando exista `tasks`, el evento `sales.followup_created.v1`
podra integrarse sin cambiar el dominio.

## Endpoints

- `GET /api/v1/sales/opportunities/`
- `POST /api/v1/sales/opportunities/`
- `GET /api/v1/sales/call-requests/`
- `POST /api/v1/sales/call-requests/{id}/mark-scheduled/`

## Workers

- `sales.generate_sales_reply`
- `sales.handle_objection`
- `sales.create_followup_task`
- `sales.notify_owner_for_hot_lead`

