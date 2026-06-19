# AI Gateway

El backend expone una interfaz propia para IA:

- `generate_reply`
- `extract_lead_data`
- `score_lead`
- `summarize_conversation`
- `transcribe_audio`
- `generate_image`
- `classify_intent`
- `create_task_candidates`

## Objetivo

Evitar que el dominio quede acoplado a OpenAI o Anthropic. Los workflows del CRM piden capacidades; el gateway decide proveedor, modelo, fallback y registro de `AIRun`.

## Uso inicial recomendado

- OpenAI: transcripcion, imagenes, tool calling.
- Anthropic: razonamiento largo, analisis comercial, respuestas consultivas.
- Fallback: provider secundario cuando falle el primario o supere latencia/costo.
