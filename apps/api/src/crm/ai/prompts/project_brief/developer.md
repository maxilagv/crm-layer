# Formato de salida

Devolvé un único JSON con esta forma (sin texto adicional):

- **title**: nombre corto del proyecto.
- **summary**: 1–2 frases de qué es el proyecto.
- **objectives**: lista de objetivos de negocio.
- **scope**: lista de lo que incluye el alcance.
- **deliverables**: lista de entregables concretos.
- **milestones**: lista de `{name, detail}` (etapas con una breve descripción).
- **open_questions**: lista de preguntas/datos que faltan definir.
- **estimated_timeline**: plazo estimado (texto) o "A confirmar".
- **estimated_budget**: presupuesto estimado (texto) o "A confirmar".
- **next_steps**: lista de próximos pasos.

## Template
Negocio: {business_name} (dueño: {owner_name})
Pista de presupuesto/valor (si la hay): {deal_value_hint}

Resumen de la conversación:
{conversation_summary}

Conversación reciente (orden cronológico):
{recent_messages}
