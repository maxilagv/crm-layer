# Cazador Voice Roadmap

La fase de voz queda diferida.

Diseño recomendado: modelo `VoiceCall` con proveedor inyectable, webhook de eventos y purpose
`voice_call` para guion/resumen. Evaluar Vapi o Retell con voces ElevenLabs; ambos cobran por
minuto, por lo que deben quedar detrás de opt-in por campaña, pausa global, horario configurable,
tope diario/mensual de llamadas, opt-out y auditoría antes de cualquier envío real.
