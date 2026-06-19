# Modelo de datos inicial

Entidades base:

- `Contact`: persona o empresa identificada por telefono.
- `ClientProfile`: datos especificos de cliente.
- `Lead`: oportunidad comercial asociada a un contacto.
- `Conversation`: hilo por canal.
- `Message`: mensaje entrante o saliente.
- `MediaAsset`: audio, imagen o documento asociado a mensaje.
- `LeadScore`: scoring historico 0-100.
- `Ticket`: incidente de soporte.
- `Task`: pendiente operativo.
- `Reminder`: recordatorio de tarea.
- `PromptVersion`: version de prompt.
- `AIRun`: ejecucion de IA auditable.
- `KnowledgeEmbedding`: contenido indexado en pgvector.
- `Notification`: notificacion saliente.
- `AuditLog`: registro de acciones y cambios.

## Principios

- PostgreSQL es la fuente de verdad.
- JSONB se usa para extracciones flexibles, no para reemplazar campos criticos.
- Las salidas IA siempre se guardan con contexto, version de prompt y estado.
- El scoring guarda componentes, explicacion y salida cruda.
