# Codex — Lote: control por chat + derivación al closer + durabilidad de prompts

Contexto: el dueño quiere (a) preguntar por WhatsApp "¿cuántos prospectos tenemos?" y recibir el
**número real** (hoy el asistente promete "te lo paso" y no lo hace — ya se mitigó por prompt, falta
el dato real), (b) que cuando un prospecto muestre interés real se **derive al closer** Ezequiel
Lavagetto (WhatsApp 1158842888), y (c) que los cambios de identidad ya hechos en la BASE no se pierdan
en un re-seed. Backend Django desplegado en el VPS. Trabajar en rama nueva; NO commitear/pushear ni
deployar salvo que se pida; tests verdes.

Entorno y convenciones: ver los prompts previos del repo (venv apps/api/.venv, settings test, pytest
--reuse-db, ruff, makemigrations --check sin drift; todo IA por AIGateway; servicios que nunca rompen
el flujo; multi-tenant por organization_id; settings por organización).

## A) Owner-assistant responde stats reales de prospecting (SIN tool-loop)

El asistente del dueño usa `AIPurpose.ASSISTANT_REPLY` con `generate_structured` (no tool-calling).
La vía simple y robusta es **inyectar las cifras en el contexto**, no un tool.

1. `crm/ai/services/context_builder.py`: nuevo helper `_prospecting_stats(organization_id) -> str`
   que arme un bloque compacto con UNA agregación barata:
   `Prospect.objects.filter(organization_id=...).values("status").annotate(n=Count("id"))`.
   Devolver algo tipo: "Prospectos hoy: 180 total · 60 calificados · 39 aprobados · 0 contactados ·
   0 respondieron · 0 interesados". Cachear ~60s con `cache.get_or_set(f"pstats:{org}", ...)`
   (patrón ya usado). Si no hay prospectos: "Todavía no hay prospectos cargados.".
2. Inyectar `"prospecting_stats": cls._prospecting_stats(organization_id)` en
   `for_assistant_reply` (context_builder.py ~:303-316).
3. En `crm/ai/prompts/assistant_agent/system.md` agregar una línea que exponga el dato, ej:
   "Cifras en vivo del Cazador (usalas si te preguntan números): {prospecting_stats}".
   Agregar `"prospecting_stats"` a `ALLOWED["assistant_agent"]` en
   `tests/unit/test_prompt_render_safety.py`. (El placeholder debe estar provisto 1:1 o
   `PromptRenderer.render` levanta `AIPromptRenderError`.)
4. Tests: `for_assistant_reply` incluye el bloque con las cifras correctas; org vacía → texto de
   "sin prospectos"; aislamiento por organización; render-safety pasa. Sin HTTP.
   Resultado: el dueño pregunta "¿cuántos prospectos?" y el modelo ya tiene el número en contexto;
   combinado con la regla de honestidad ya activa, responde la cifra real.

(Opcional, después: un `prospecting_stats` TOOL scopeado a assistant_reply para consultas más ricas,
siguiendo el patrón de `crm/ai/tools/` — ToolDefinition + BaseTool.execute + register_tool +
allowed_purposes. Pero la vía de contexto ya resuelve "cuántos prospectos".)

## B) Derivar al closer (Ezequiel) cuando hay interés real

El closer ya está guardado en `BusinessProfile.metadata["closer"]` =
`{"name": "Ezequiel Lavagetto", "whatsapp": "1158842888", "role": "vendedor clasificado / closer"}`.
Hoy, cuando un prospecto se vuelve INTERESTED / dispara handoff, el sistema notifica al OWNER
(`NotificationService.notify_owner` → OWNER_WHATSAPP_NUMBER). Sumar la derivación al closer:

1. En el camino de interés/handoff de prospectos (`crm/prospecting/services/replies.py` →
   `crm/prospecting/services/conversation_engine.py handle_inbound_next_step`, donde se marca
   INTERESTED / se crea lead / se notifica), leer el closer de `BusinessProfile.metadata["closer"]`
   (helper que tolere ausencia → si no hay closer, comportamiento actual).
2. Enviar al WhatsApp del closer (vía el outbound queue del bridge, igual que el outreach) un
   mensaje de derivación con el contexto del prospecto: nombre del negocio, teléfono, rubro, y un
   resumen de qué quiere (1-2 líneas). Idempotente (dedupe por prospect_id + "derivacion") para no
   re-derivar. Mantener también la notificación al owner.
3. Hacer el número del closer configurable (preferible un campo en SalesPolicy/BusinessProfile en vez
   de solo metadata; migración simple) — pero leer de metadata como fallback para no romper lo ya
   guardado.
4. Tests (fakes, sin envío real): prospecto pasa a INTERESTED → se encola 1 derivación al número del
   closer con el contexto correcto; segunda vez no re-deriva (idempotencia); sin closer configurado →
   no rompe y solo notifica al owner.

## C) Durabilidad: sincronizar los prompts vivos al repo

Durante el loop se editaron en la BASE (vía PromptRegistry.create_draft + activate_version) los
prompts del org `web-layer`: `outreach_opener` (identidad Octavio Fuentes del equipo de LayerCloud +
diferencial "sistemas que aprenden"), `outreach_reply` (misma identidad + derivación a Ezequiel) y
`assistant_reply` (regla de honestidad: no prometer async, decir si no tiene la cifra). El
`outreach_opener/system.md` del repo ya tiene el diferencial pero NO la identidad Octavio.
Acción: actualizar los `.md` del repo para que reflejen las versiones vivas, así un futuro
`ai_seed_prompts`/`ai_update_prompts` no revierta los cambios:
- `crm/ai/prompts/outreach_opener/system.md` → identidad "Octavio Fuentes del equipo de {business_name}"
  + sección de equipo + saludo "soy Octavio Fuentes del equipo de {business_name}".
- `crm/ai/prompts/outreach_reply/system.md` → identidad Octavio/equipo + sección "qué vendés" +
  derivación a Ezequiel con handoff.
- `crm/ai/prompts/assistant_agent/system.md` → sección "Honestidad con los datos" (anti "te lo paso").
(Pedir al dueño/Claude las versiones exactas vivas, o leerlas de la DB del org con un management
command de export, para copiarlas tal cual.) Bumpear `test_prompt_render_safety.py` si se agregan
placeholders nuevos ({prospecting_stats}).

## D) (Después) Investigación profunda antes del opener

Un paso de "deep research" por prospecto que, antes de redactar el opener, corra un análisis OpenAI
de su huella digital (web + redes si están disponibles: Instagram/Facebook/Google) y le pase
insights al opener para un primer mensaje quirúrgico. Va de la mano del roadmap RAG (ver el prompt de
Fase 1 ya entregado: pgvector + crm.knowledge). No bloquea A/B/C.

## Definición de hecho
makemigrations --check sin drift · ruff limpio · pytest --reuse-db verde (incluye los tests nuevos de
A y B + render-safety) · el asistente responde cifras reales · derivación al closer encola y es
idempotente · prompts del repo sincronizados con lo vivo. Adopción en vivo (supervisada): migrate +
recreate api/worker + (si se tocó ai_update_prompts) re-adoptar prompts con cuidado de no pisar lo vivo.
