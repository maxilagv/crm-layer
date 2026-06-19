# Seguridad

Este CRM procesa conversaciones, datos comerciales, tickets de soporte, audios, imagenes y salidas de modelos IA. Se trata como sistema privado con datos sensibles.

## Principios

- WhatsApp webhooks y workers criticos viven en Python, no en Next.js.
- Todo evento importante se guarda en PostgreSQL antes de invocar IA cuando sea posible.
- La IA no es fuente de verdad: sus extracciones se guardan con confianza, version de prompt y auditoria.
- Las credenciales nunca se versionan. Usar `.env` local y secretos del proveedor en produccion.
- Los mensajes proactivos de WhatsApp deben respetar ventana de 24 horas y plantillas aprobadas.

## Reporte de problemas

Mientras el proyecto sea privado, registrar hallazgos de seguridad en `docs/security/` y convertirlos en tareas tecnicas antes de desplegar.
