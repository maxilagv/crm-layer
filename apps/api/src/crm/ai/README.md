# crm.ai — Plataforma interna de IA

Módulo que centraliza TODO el uso de IA del backend: proveedores, modelos por
propósito, prompts versionados, structured outputs, tool calling autorizado,
SafetyGuard, costos, auditoría, evals y fallback.

## Regla de oro

**Ningún módulo de negocio importa `openai` ni `anthropic`.** La única frontera
con los SDKs es `crm/ai/providers/`. El test
`tests/unit/test_ai_no_direct_provider_imports.py` escanea el código y falla si
aparece un import directo fuera de esa carpeta.

La interfaz estable es `AIGateway` (`crm.ai.services.ai_gateway`):

```python
from crm.ai.services.ai_gateway import AIGateway

result = AIGateway.generate_sales_reply(conversation_id=..., message_id=...)
if result.can_send_reply:
    enviar(result.data["reply"])
elif result.safety and result.safety.requires_handoff:
    derivar_a_humano()
```

Métodos: `generate_sales_reply`, `generate_support_reply`, `score_lead`,
`extract_tasks`, `summarize_conversation`, `transcribe_audio`,
`extract_ticket_from_audio`, `generate_image`, `create_embedding`,
`classify_risk`. Todos devuelven `AIGatewayResult` (nunca respuestas crudas).

## Flujo de cada llamada

route (ModelRouter) → contexto (ContextBuilder) → prompt activo
(PromptRegistry + PromptRenderer) → **AIRun creado antes de llamar** → provider
(con fallback ante timeout/rate-limit/outage) → validación structured output
(1 retry de reparación; 2 fallos = `schema_invalid`, **nada toca la base**) →
tools autorizadas (ToolExecutor) → SafetyGuard → usage/costo → AIRun final.

## Cómo agregar un provider

1. Crear `crm/ai/providers/<nombre>_provider.py` heredando `BaseAIProvider`.
2. Normalizar todo a `AIRequest`/`AIResponse`; mapear errores con
   `provider_errors.normalize_provider_exception`. Ningún tipo del SDK sale.
3. Registrar en `provider_factory._PROVIDERS` y en `AIProviderType`.
4. Lazy import del SDK. API key SOLO desde settings/env.

## Cómo crear y versionar un prompt

- Los prompts iniciales viven en `crm/ai/prompts/<carpeta>/` (`system.md`,
  `developer.md` con `## Template`, `schema.json`, `examples.yaml`, `README.md`)
  y se siembran con `python manage.py ai_seed_prompts` (idempotente).
- Después del seed, el ciclo de vida es por DB/API: crear draft
  (`POST /api/v1/ai/prompts/{id}/versions/`), activar
  (`POST .../versions/{vid}/activate/`). Activar archiva la versión anterior;
  **una versión activa es inmutable** (lo garantiza el modelo). Cada `AIRun`
  guarda `prompt_version_id`. Cada activación queda auditada.

## Cómo agregar una tool

1. Crear `crm/ai/tools/<nombre>.py` con un `BaseTool` que declare
   `ToolDefinition` (schema de argumentos, permisos, purposes permitidos,
   side effects, `idempotency_scope`, `audit_event`, riesgo).
2. Registrarla en `tools/__init__.register_builtin_tools`.
3. El modelo solo PIDE la tool; `ToolExecutor` valida existencia → argumentos →
   purpose → permisos (rol AI_AGENT si no hay actor humano) → idempotencia →
   ejecuta → registra `AIToolCall` → audita. `send_whatsapp_message` pasa por
   SafetyGuard antes de encolar. Módulos que aún no existen (leads Fase 6,
   tickets Fase 7) fallan con `tool_module_unavailable`; `create_task` /
   `notify_owner` / `create_call_request` persisten eventos outbox reales que
   consumirá Fase 8.

## SafetyGuard

Reglas determinísticas en `services/safety_guard.py` + keywords en
`domain/policies.py` (revisables en git): pedido de contraseña y promesas
garantizadas → `do_not_reply`; precio sin política autorizada (lee
`SalesPolicy.can_quote_prices`) y datos sensibles en la respuesta → `revise`;
amenaza legal / cliente furioso / operación sensible → `handoff_to_human`;
incidente crítico → handoff + `notify_owner`. `classify_risk` combina estas
reglas con el clasificador por modelo y se queda SIEMPRE con el peor veredicto.
La seguridad nunca depende solo del modelo.

## Costos y observabilidad

Cada llamada persiste `AIRun` (mensajes, contexto, output, latencia, error,
safety) y `AIUsageRecord` (tokens/audio/imágenes + costo estimado por la tabla
de `services/cost_tracker.py`, sobreescribible vía `settings.AI_COST_TABLE`;
recalculable con `python manage.py ai_recalculate_usage`). Consultas:
`GET /api/v1/ai/usage/`, `/by-purpose/`, `/by-model/`, `/by-day/` y selectors
en `selectors/costs.py` (runs fallidos, bloqueados por safety).

## Evals

Datasets en `evals/datasets/*.yaml`. Correr:

```bash
python manage.py ai_run_evals --organization-id <uuid> [--suite sales_agent]
# o por API: POST /api/v1/ai/evals/run/
```

Resultados persistidos en `AIEvalResult` con métricas (`schema_validity_rate`,
decisiones de safety, conteo de tareas). Determinísticos: jamás llaman
proveedores reales.

## Tests

```bash
pytest tests/unit/test_ai_*.py tests/api/test_ai_api.py
```

Todos los tests usan `FakeAIProvider` (comportamientos: respuesta válida,
schema inválido, timeout, rate limit, outage, tool call, tool no autorizada,
respuesta bloqueable). Cero llamadas reales.

## Setup local rápido

```bash
python manage.py ai_seed_fake_provider   # provider fake + configs por purpose
python manage.py ai_seed_prompts         # prompts iniciales v1 activos
```

Para producción: crear `AIProvider` openai/anthropic + `AIModelConfig` por
propósito (vía admin o API). Las API keys viven SOLO en variables de entorno
(`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`); `AIProvider.metadata` no debe
contener secretos. Si en el futuro se necesitan keys por organización, debe
agregarse primero un módulo de cifrado (interfaz pendiente, documentado aquí
como limitación).

## Embeddings

`AIEmbedding.vector` es JSON (lista de floats) por compatibilidad. Próximo paso
documentado: migrar a `pgvector.django.VectorField` + índice ivfflat cuando
llegue retrieval por similitud (la extensión ya está en la imagen de Postgres).
