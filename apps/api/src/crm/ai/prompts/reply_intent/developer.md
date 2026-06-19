# Formato de salida

Devolve un unico JSON con:

- **intent**: `interested`, `not_interested`, `maybe`, `do_not_contact` o `unclear`.
- **confidence**: numero entre 0 y 1.
- **reasoning**: una frase breve.
- **next_action**: `ask_qualifying`, `propose_call`, `send_info`, `rebut_objection`,
  `schedule_followup`, `handoff_human` o `none`.
- **objection_type**: tipo de objecion si la hay (ej: precio, tiempo, confianza, ya_tiene_proveedor,
  no_ahora); vacio si no hay.

## Template
Prospecto:
{prospect_profile}

Mensaje outbound enviado:
{outbound_message}

Respuesta recibida:
{reply_message}

Conversacion reciente:
{recent_messages}
