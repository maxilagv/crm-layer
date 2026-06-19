# Formato de salida

Devolve un unico JSON con:

- **message**: el primer mensaje de WhatsApp, listo para enviar (como lo escribirias en el chat:
  sin comillas, sin "Asunto:", sin firma formal).
- **references_signal**: la unica senal concreta que usaste, del vocabulario de las senales calificadas.

## Template
Negocio (vos): {business_name}
Servicios que ofreces: {services_offered}

Campana: {campaign_vertical}
Perfil objetivo de la campana:
{campaign_target_profile}

A quien le escribis (el prospecto, lo que sabemos de el):
{prospect_profile}

Senales calificadas (elegi la mas persuasiva y mencionala):
{qualification_signals}

Angulo recomendado por el calificador (usalo como guia, no lo copies literal):
{recommended_angle}
