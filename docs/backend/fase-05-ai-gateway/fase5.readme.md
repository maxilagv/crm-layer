# Fase 5: AI Gateway, prompts, tools y guardrails

## Objetivo

Crear la plataforma interna de IA. Esta es una de las fases mas delicadas. El error comun seria llamar a OpenAI desde cualquier service. Eso no debe pasar.

Todo uso de IA debe pasar por un unico modulo:

```text
ai
```

Este modulo maneja proveedores, modelos, prompts, costos, seguridad, structured outputs, tool calling, auditoria, evaluaciones y fallback.

## Resultado esperado

Al terminar esta fase el backend debe poder:

- usar OpenAI, Anthropic o fake provider sin cambiar modulos de negocio;
- elegir modelo por proposito;
- versionar prompts;
- renderizar prompts con contexto controlado;
- validar salidas estructuradas;
- registrar cada llamada IA;
- medir latencia y costo;
- ejecutar tools solo si el backend autoriza;
- aplicar SafetyGuard;
- usar fallback provider;
- correr evals basicas;
- explicar por que una IA respondio algo.

## Modulos involucrados

- `ai`
- `settings`
- `audit`
- `media` basico
- `conversations`
- `core`

## Estructura

```text
crm/modules/ai/
|-- models.py
|-- providers/
|   |-- base.py
|   |-- openai_provider.py
|   |-- anthropic_provider.py
|   \-- fake_provider.py
|-- prompts/
|   |-- registry.py
|   |-- sales_agent/
|   |-- support_agent/
|   |-- lead_scoring/
|   |-- task_extraction/
|   |-- audio_ticket_extraction/
|   |-- conversation_summary/
|   \-- image_generation/
|-- schemas/
|   |-- sales_reply.py
|   |-- support_reply.py
|   |-- lead_score.py
|   |-- task_candidate.py
|   |-- support_ticket.py
|   |-- conversation_summary.py
|   \-- moderation_result.py
|-- tools/
|   |-- create_task.py
|   |-- update_lead.py
|   |-- create_ticket.py
|   |-- send_whatsapp_message.py
|   |-- notify_owner.py
|   |-- pause_conversation_ai.py
|   \-- generate_image.py
|-- services/
|   |-- ai_gateway.py
|   |-- model_router.py
|   |-- prompt_renderer.py
|   |-- structured_output.py
|   |-- tool_registry.py
|   |-- tool_executor.py
|   |-- safety_guard.py
|   |-- cost_tracker.py
|   |-- embedding_service.py
|   |-- context_builder.py
|   \-- eval_runner.py
|-- evals/
|   |-- datasets/
|   \-- cases/
\-- tasks.py
```

## Modelos

Modelos esperados:

- `ai_provider`;
- `ai_model_config`;
- `ai_prompt`;
- `ai_prompt_version`;
- `ai_run`;
- `ai_message`;
- `ai_tool_call`;
- `ai_usage_record`;
- `ai_embedding`;
- `ai_eval_case`;
- `ai_eval_result`.

### AIProvider

Campos:

- `id`;
- `organization_id`;
- `name`;
- `provider_type`;
- `is_enabled`;
- `priority`;
- `metadata`;
- `created_at`;
- `updated_at`.

Tipos:

- `openai`;
- `anthropic`;
- `fake`.

### AIModelConfig

Campos:

- `id`;
- `organization_id`;
- `provider_id`;
- `purpose`;
- `model_name`;
- `temperature`;
- `max_tokens`;
- `timeout_seconds`;
- `fallback_model`;
- `is_active`;
- `metadata`.

Purposes:

- `sales_reply`;
- `support_reply`;
- `lead_scoring`;
- `task_extraction`;
- `audio_transcription`;
- `conversation_summary`;
- `image_generation`;
- `embedding`.

### AIPrompt

Campos:

- `id`;
- `organization_id`;
- `key`;
- `name`;
- `description`;
- `purpose`;
- `active_version_id`;
- `created_at`;
- `updated_at`.

### AIPromptVersion

Campos:

- `id`;
- `prompt_id`;
- `version`;
- `status`;
- `system_prompt`;
- `developer_prompt`;
- `template`;
- `output_schema`;
- `examples`;
- `created_by_id`;
- `activated_at`;
- `archived_at`;
- `created_at`.

Estados:

- `draft`;
- `active`;
- `archived`.

### AIRun

Campos:

- `id`;
- `organization_id`;
- `provider`;
- `model`;
- `purpose`;
- `input_messages`;
- `output_text`;
- `output_json`;
- `tool_calls`;
- `usage_input_tokens`;
- `usage_output_tokens`;
- `estimated_cost`;
- `latency_ms`;
- `status`;
- `error_message`;
- `prompt_version_id`;
- `conversation_id`;
- `message_id`;
- `contact_id`;
- `created_at`.

### AIToolCall

Campos:

- `id`;
- `organization_id`;
- `ai_run_id`;
- `tool_name`;
- `arguments`;
- `result`;
- `status`;
- `error_message`;
- `started_at`;
- `finished_at`;
- `created_at`.

## API interna del gateway

El gateway debe exponer metodos internos claros:

```text
AIGateway.generate_sales_reply()
AIGateway.generate_support_reply()
AIGateway.score_lead()
AIGateway.extract_tasks()
AIGateway.summarize_conversation()
AIGateway.transcribe_audio()
AIGateway.generate_image()
AIGateway.create_embedding()
AIGateway.classify_risk()
```

Ningun otro modulo deberia saber si eso usa OpenAI, Anthropic o fake provider.

## Structured outputs

Todo lo que actualice base debe volver estructurado.

Ejemplo para lead scoring:

```json
{
  "score": 82,
  "temperature": "hot",
  "pain_points": [
    "pierde leads por demora",
    "necesita automatizacion de WhatsApp"
  ],
  "urgency": "high",
  "budget_signal": "unknown",
  "authority_signal": "likely_decision_maker",
  "next_best_action": "propose_call",
  "confidence": 0.87
}
```

Ejemplo para respuesta comercial:

```json
{
  "reply": "texto a enviar al lead",
  "intent": "book_call",
  "lead_updates": {},
  "suggested_tasks": [],
  "should_notify_owner": true,
  "should_handoff": false,
  "risk_level": "low",
  "confidence": 0.91
}
```

## Tool calling interno

Herramientas iniciales:

- `create_task`;
- `update_lead`;
- `create_ticket`;
- `notify_owner`;
- `send_whatsapp_message`;
- `pause_conversation_ai`;
- `create_call_request`;
- `generate_image`.

Regla: el modelo puede solicitar una herramienta, pero el backend decide si se ejecuta.

Cada tool debe declarar:

- nombre;
- version;
- schema de argumentos;
- permisos requeridos;
- side effects;
- idempotency scope;
- audit event;
- service ejecutor.

## SafetyGuard

Debe evaluar:

- riesgo comercial;
- riesgo legal;
- datos sensibles;
- cliente enojado;
- amenaza legal;
- precio no autorizado;
- promesa falsa;
- necesidad de humano;
- mensaje ambiguo.

Decisiones posibles:

- `send`;
- `revise`;
- `ask_clarifying_question`;
- `handoff_to_human`;
- `do_not_reply`;
- `notify_owner`.

## Cost tracking

Cada llamada debe registrar:

- modelo;
- proveedor;
- tokens de entrada;
- tokens de salida;
- costo estimado;
- latencia;
- proposito;
- contacto;
- conversacion.

Esto alimenta analytics y evita que el costo de IA quede invisible.

## Prompt registry

Prompts iniciales:

- `sales_agent_v1`;
- `support_agent_v1`;
- `lead_scoring_v1`;
- `task_extraction_v1`;
- `audio_ticket_extraction_v1`;
- `conversation_summary_v1`;
- `risk_classifier_v1`;
- `image_generation_v1`.

Cada prompt debe tener:

- `system.md`;
- `developer.md`;
- `schema.json`;
- `examples.yaml`;
- `README.md`.

## Fake provider

Debe existir `FakeAIProvider` para tests.

Los tests no deben depender de OpenAI ni Anthropic. El fake provider debe poder devolver:

- respuesta valida;
- schema invalido;
- timeout;
- provider error;
- tool call;
- safety issue.

## Endpoints

```text
GET  /api/v1/ai/runs/
GET  /api/v1/ai/runs/{id}/

GET  /api/v1/ai/prompts/
POST /api/v1/ai/prompts/
GET  /api/v1/ai/prompts/{id}/
POST /api/v1/ai/prompts/{id}/versions/
POST /api/v1/ai/prompts/{id}/activate/

GET  /api/v1/ai/model-configs/
PATCH /api/v1/ai/model-configs/{id}/

POST /api/v1/ai/evals/run/
GET  /api/v1/ai/evals/results/
```

## Workers

- `ai.generate_sales_reply`;
- `ai.generate_support_reply`;
- `ai.score_lead`;
- `ai.extract_tasks`;
- `ai.summarize_conversation`;
- `ai.transcribe_audio`;
- `ai.generate_image`;
- `ai.create_embeddings`;
- `ai.run_eval_suite`.

## Tests obligatorios

- `test_ai_gateway_uses_configured_provider`;
- `test_ai_gateway_fallback_provider`;
- `test_prompt_version_activation`;
- `test_ai_run_is_logged`;
- `test_structured_output_validation`;
- `test_invalid_schema_rejected`;
- `test_tool_call_requires_permission`;
- `test_safety_guard_blocks_forbidden_price_claim`;
- `test_cost_tracker_records_usage`;
- `test_fake_provider_for_tests`.

## Criterios de perfeccion

La fase 5 esta perfecta cuando:

1. Ningun modulo llama directo a OpenAI o Anthropic.
2. Todo uso de IA pasa por AIGateway.
3. Los prompts estan versionados.
4. Los modelos se configuran por proposito.
5. Cada llamada IA queda registrada.
6. Cada costo queda estimado.
7. Cada output estructurado se valida.
8. Las tools estan registradas.
9. Las tools tienen permisos.
10. El SafetyGuard puede bloquear respuestas.
11. Existe fallback de proveedor.
12. Existe fake provider para tests.
13. Existen prompts iniciales.
14. Existen evals iniciales.
15. El sistema puede explicar por que una IA respondio algo.

## Riesgos a evitar

- llamar OpenAI desde leads/support/tasks directamente;
- usar prompts sin version;
- parsear texto libre para actualizar base;
- ejecutar tools porque el modelo lo pidio sin validar;
- no registrar costo;
- no tener fake provider;
- usar temperatura alta para extracciones estructuradas;
- guardar secretos de proveedores en base sin proteccion.

## Recomendacion de division en subfases

### Fase 5.1: Provider abstraction

Entregables:

- interface base;
- OpenAIProvider;
- AnthropicProvider;
- FakeAIProvider;
- ModelRouter.

Validacion:

- tests de provider seleccionado;
- tests de fallback;
- tests de timeout.

### Fase 5.2: Model configs y AI runs

Entregables:

- AIProvider;
- AIModelConfig;
- AIRun;
- usage records;
- cost tracker.

Validacion:

- test de AIRun success;
- test de AIRun failed;
- test de costo estimado.

### Fase 5.3: Prompt versioning

Entregables:

- AIPrompt;
- AIPromptVersion;
- activacion;
- archivado;
- renderer.

Validacion:

- test de version activa;
- test de no editar historico;
- test de rendering.

### Fase 5.4: Structured outputs

Entregables:

- schemas por proposito;
- validator;
- retry on invalid schema;
- error taxonomy.

Validacion:

- output valido aceptado;
- output invalido rechazado;
- retry controlado.

### Fase 5.5: Tools

Entregables:

- registry;
- executor;
- permisos;
- idempotencia;
- audit log.

Validacion:

- tool permitida ejecuta;
- tool sin permiso se bloquea;
- tool fallida registra error;
- tool idempotente no duplica.

### Fase 5.6: SafetyGuard

Entregables:

- risk classifier;
- reglas deterministicas;
- decisiones send/revise/handoff;
- logs.

Validacion:

- precio no autorizado bloqueado;
- amenaza legal deriva;
- mensaje ambiguo pide aclaracion.

### Fase 5.7: Evals iniciales

Entregables:

- datasets base;
- eval runner;
- metricas iniciales;
- reporte de resultados.

Validacion:

- suite corre con fake provider;
- casos minimos de venta/soporte/tareas;
- resultados persistidos.
