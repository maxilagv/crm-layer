# Decisiones de Horizonte 0

Este archivo es el checklist funcional que debe quedar cerrado antes del MVP conversacional.

## Identidad

- Nombre del sistema: pendiente.
- Dominio de produccion: pendiente.
- Numero de WhatsApp Business: pendiente.
- Numero personal para notificaciones: pendiente.

## Oferta comercial

- Servicios vendidos: pendiente.
- Servicios que no se venden: pendiente.
- Rango de precios comunicable por IA: pendiente.
- Casos donde la IA debe derivar sin vender: pendiente.

## Estados

Estados iniciales de lead:

- `new`
- `contacted`
- `qualified`
- `proposal`
- `won`
- `lost`
- `nurture`

Estados iniciales de cliente:

- `active`
- `paused`
- `at_risk`
- `churned`

## Politica de IA

La IA puede responder cuando:

- el mensaje entra por WhatsApp;
- no hay bloqueo manual activo;
- el contacto no requiere handoff humano;
- la respuesta cumple reglas de tono, precio y alcance.

La IA deriva a humano cuando:

- hay enojo, reclamo fuerte o amenaza legal;
- se pide informacion sensible;
- se solicita precio cerrado fuera de reglas;
- el score del lead supera el umbral que definamos;
- el cliente reporta incidente urgente;
- el modelo declara baja confianza.

## Datos guardados

Todo mensaje, extraccion, decision automatica, prompt y accion enviada debe quedar persistido con timestamp y referencia al contacto/conversacion.
