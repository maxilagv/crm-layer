# Arquitectura del sistema

El CRM tiene WhatsApp como interfaz principal y un panel web como consola operativa. La autoridad del negocio vive en `apps/api`.

## Componentes

- Next.js: panel admin, inbox, leads, clientes, tickets, tareas, prompts, metricas, imagenes y control manual.
- Django REST Framework: API, admin, permisos, entidades CRM y endpoints internos.
- Celery: procesamiento asincronico de webhooks, audios, scoring, tareas, notificaciones y evaluaciones IA.
- Redis: broker y backend de resultados Celery.
- PostgreSQL + pgvector: fuente de verdad transaccional y busqueda semantica.
- Object storage: audios, imagenes, documentos y assets generados.
- AI Gateway: capa interna para OpenAI/Anthropic sin acoplar dominio a proveedores.
- Caddy/Nginx: proxy reverso y TLS en VPS.

## Flujo de WhatsApp

1. Meta llama al webhook de Django.
2. Django valida firma y guarda evento/mensaje.
3. Celery procesa el evento.
4. CRM Core identifica contacto, conversacion y modo: lead, cliente, proveedor o interno.
5. AI Gateway clasifica, resume, extrae datos o propone respuesta.
6. Reglas de negocio deciden responder, derivar, crear ticket, crear tarea o notificar.
7. Se audita la accion y se envia por WhatsApp si corresponde.

## Regla de propiedad

Next.js nunca debe recibir webhooks criticos ni coordinar workers. Su rol es visualizar, operar y controlar.
