# Limites de modulos

## `apps/api`

Responsable de:

- webhooks criticos;
- persistencia;
- modelos de dominio;
- reglas de negocio;
- Celery workers;
- scoring;
- transcripcion;
- envio de WhatsApp;
- tareas automaticas;
- tickets;
- auditoria;
- AI Gateway.

No responsable de:

- layout del panel;
- estado local de UI;
- interacciones visuales.

## `apps/web`

Responsable de:

- panel de administracion;
- inbox;
- vista de leads/clientes/tickets/tareas;
- prompt manager;
- metricas;
- generador de imagenes;
- control manual de conversaciones;
- auditoria visual.

No responsable de:

- webhooks de WhatsApp;
- colas;
- scoring;
- coordinacion de agentes;
- mensajes proactivos.

## `packages/contracts`

Responsable de:

- enums compartidos;
- schemas compartidos;
- tipos de DTOs;
- contratos estables entre web y API.
