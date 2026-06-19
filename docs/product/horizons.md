# Horizontes de desarrollo

## Horizonte 0: definicion funcional

Objetivo: cerrar que hace y que no hace el sistema antes de implementar flujos criticos.

Decisiones pendientes:

- nombre del sistema;
- numero de WhatsApp;
- estados de lead;
- estados de cliente;
- servicios vendidos;
- tono comercial;
- cuando responde IA;
- cuando deriva a humano;
- datos que se guardan;
- plantillas de WhatsApp necesarias.

## Horizonte 1: MVP conversacional

Objetivo: recibir WhatsApp, guardar conversaciones y responder leads/clientes.

Incluye webhook de WhatsApp, PostgreSQL, contactos, conversaciones, clasificador lead/cliente, modo vendedor basico, modo cliente basico, notificacion al numero propio y panel admin simple.

## Horizonte 2: audio + tickets

Objetivo: transformar audios de errores en texto util y tickets.

Incluye descarga de audios, transcripcion, resumen tecnico, ticket, prioridad, respuesta automatica al cliente y notificacion interna.

## Horizonte 3: lead scoring y ventas avanzadas

Objetivo: convertir el bot en vendedor consultivo.

Incluye scoring 0-100, objeciones, preguntas de diagnostico, deteccion de intencion fuerte, propuesta de llamada, seguimiento automatico e historial comercial.

## Horizonte 4: gestor de tareas

Objetivo: que el sistema sea asistente operativo.

Incluye extraccion automatica de tareas, recordatorios, estados, confirmacion por WhatsApp, escalamiento y vista diaria.

## Horizonte 5: generacion de imagenes

Objetivo: crear assets comerciales desde el CRM.

Incluye generador de portadas, prompts reutilizables, biblioteca, envio por WhatsApp y plantillas por cliente/campaña.

## Horizonte 6: hardening

Objetivo: hacerlo confiable.

Incluye backups, monitoreo, auditoria, roles, permisos, tests, prompt versioning, evaluacion de respuestas, metricas y fallbacks de proveedor IA.
