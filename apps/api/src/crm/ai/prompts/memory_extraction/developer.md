# Formato de salida

Devolvé un único JSON con la forma `{"facts": [{memory_type, content, importance, expires_in_days}]}`. Nada de texto fuera del JSON.

- **memory_type**: uno de `preference`, `pain_point`, `technical_context`, `commercial_context`, `support_context`, `objection`, `commitment`.
- **content**: el hecho, en una frase clara y reutilizable.
- **importance**: entero 1–5.
- **expires_in_days**: entero o `null`.

## Template
Negocio: {business_name}
Contacto: {contact_name}

Resumen de la conversación:
{conversation_summary}

Memoria ya guardada de este contacto (NO la repitas):
{existing_memories}

Conversación reciente (orden cronológico):
{recent_messages}
