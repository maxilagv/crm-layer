# Seguridad de WhatsApp e IA

## WhatsApp

- Validar `X-Hub-Signature-256` en cada webhook.
- Guardar payload crudo antes de procesar.
- Deduplicar por `message_id`.
- Respetar ventana de 24 horas.
- Usar plantillas aprobadas fuera de ventana.
- Mantener escalamiento humano claro.

## IA

- No permitir que el modelo ejecute acciones sin validacion de reglas.
- Guardar input, output, proveedor, modelo, version de prompt y latencia.
- Separar respuesta sugerida de respuesta enviada.
- Marcar baja confianza y derivar a humano.
- No inventar precios, disponibilidad, casos de exito ni promesas.
