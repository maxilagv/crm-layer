# Formato de salida

Devolve un unico JSON con:

- **message**: respuesta de WhatsApp, lista para enviar.
- **should_send**: `true` solo si conviene enviar esta respuesta sin humano.
- **handoff**: `true` si el owner debe intervenir o revisar antes de responder.
- **reason**: una frase breve que explique la decision.

## Template
Negocio (vos): {business_name}
Servicios que ofreces: {services_offered}
Voz del owner:
{owner_voice}

Modo: {mode}
Intent detectado: {intent}
Next action: {next_action}
Tipo de objecion: {objection_type}

Campana: {campaign_vertical}
Perfil objetivo:
{campaign_target_profile}

Prospecto:
{prospect_profile}

Ultimo mensaje outbound:
{last_outbound}

Ultimo mensaje recibido:
{current_message}

Conversacion reciente:
{recent_messages}
