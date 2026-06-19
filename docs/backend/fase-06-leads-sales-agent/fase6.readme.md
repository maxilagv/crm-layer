# Fase 6: Leads, scoring y agente vendedor

Documento de implementacion actual: [implementacion.md](implementacion.md).

## Objetivo

Construir el motor comercial. Esta fase convierte conversaciones de desconocidos en oportunidades calificadas y permite que el sistema responda como vendedor tecnico profesional.

Aca aparece el modo vendedor.

## Resultado esperado

Al terminar esta fase el backend debe poder:

- convertir contactos desconocidos en leads;
- mantener pipeline comercial;
- calcular score 0-100;
- guardar snapshots historicos de scoring;
- generar respuestas comerciales con IA;
- aplicar reglas de venta;
- manejar objeciones;
- crear solicitudes de llamada;
- crear tareas de seguimiento;
- notificar leads calientes;
- convertir leads en clientes;
- auditar todo el flujo comercial.

## Modulos involucrados

- `leads`
- `sales`
- `ai`
- `conversations`
- `contacts`
- `tasks` basico
- `notifications` basico
- `audit`
- `settings`

## Modelos

Modelos esperados:

- `leads_lead`;
- `leads_lead_score_snapshot`;
- `leads_lead_stage_history`;
- `leads_lead_source`;
- `sales_opportunity`;
- `sales_followup`;
- `sales_objection`;
- `sales_playbook`;
- `sales_call_request`.

## Lead

Campos:

- `id`;
- `organization_id`;
- `contact_id`;
- `status`;
- `stage`;
- `score`;
- `temperature`;
- `service_interest`;
- `budget_signal`;
- `urgency`;
- `authority_signal`;
- `pain_points`;
- `technical_needs`;
- `business_needs`;
- `next_best_action`;
- `last_scored_at`;
- `summary`;
- `metadata`;
- `created_at`;
- `updated_at`.

Estados:

- `active`;
- `won`;
- `lost`;
- `unqualified`;
- `nurturing`;
- `archived`.

Stages:

- `new`;
- `contacted`;
- `qualifying`;
- `warm`;
- `hot`;
- `call_requested`;
- `call_scheduled`;
- `proposal_pending`;
- `won`;
- `lost`;
- `nurturing`;
- `unqualified`.

Temperature:

- `cold`;
- `warm`;
- `hot`;
- `critical`.

## LeadScoreSnapshot

Campos:

- `id`;
- `organization_id`;
- `lead_id`;
- `score`;
- `temperature`;
- `reasoning_summary`;
- `factors`;
- `ai_run_id`;
- `created_at`.

Factores:

- `pain_clear`;
- `urgency`;
- `authority`;
- `budget_signal`;
- `business_fit`;
- `engagement`;
- `technical_match`;
- `risk_penalty`.

## SalesOpportunity

Campos:

- `id`;
- `organization_id`;
- `lead_id`;
- `contact_id`;
- `title`;
- `value_estimate_min`;
- `value_estimate_max`;
- `currency`;
- `stage`;
- `probability`;
- `expected_close_date`;
- `metadata`;
- `created_at`;
- `updated_at`.

## SalesCallRequest

Campos:

- `id`;
- `organization_id`;
- `lead_id`;
- `contact_id`;
- `conversation_id`;
- `status`;
- `requested_at`;
- `scheduled_at`;
- `owner_notified_at`;
- `notes`;
- `metadata`.

Estados:

- `requested`;
- `owner_notified`;
- `scheduled`;
- `completed`;
- `cancelled`;
- `expired`.

## Scoring comercial

El scoring mezcla reglas duras e IA. La IA puede interpretar contexto, pero el backend define pesos, limites y conversion a score final.

Puntaje sugerido:

```text
pain_clear        0-20
urgency           0-15
authority         0-15
budget_signal     0-10
business_fit      0-20
engagement        0-10
technical_match   0-10
risk_penalty     -20
```

Interpretacion:

```text
0-30    frio
31-55   tibio
56-75   bueno
76-100  caliente
```

Reglas:

- score actual vive en Lead;
- cada recalculo crea LeadScoreSnapshot;
- el snapshot guarda explicacion;
- el score debe ser reproducible en tests;
- si el output IA es invalido, no se actualiza el score.

## Servicios

Servicios esperados:

- `LeadCreationService`;
- `LeadScoringService`;
- `LeadLifecycleService`;
- `LeadQualificationService`;
- `LeadFollowupService`;
- `OpportunityService`;
- `SalesConversationAgent`;
- `SalesIntentClassifier`;
- `SalesObjectionHandler`;
- `SalesCallCloser`;
- `SalesReplyPolicy`;
- `SalesMemoryBuilder`.

## SalesConversationAgent

Debe recibir:

- `conversation_history`;
- `contact_profile`;
- `lead_profile`;
- `lead_score`;
- `business_profile`;
- `sales_policy`;
- `service_catalog`;
- `previous_objections`;
- `conversation_summary`;
- `owner_preferences`.

Debe devolver:

```json
{
  "reply": "texto final para WhatsApp",
  "intent": "qualify_lead",
  "lead_updates": {},
  "suggested_tasks": [],
  "should_notify_owner": false,
  "should_handoff": false,
  "should_create_call_request": false,
  "risk_level": "low",
  "confidence": 0.88
}
```

## Intenciones comerciales

- `new_interest`;
- `asking_price`;
- `asking_how_it_works`;
- `has_problem`;
- `wants_call`;
- `objecting_price`;
- `objecting_time`;
- `not_interested`;
- `qualified`;
- `unqualified`;
- `spam`.

## Reglas del agente vendedor

Debe:

- hablar como senior tecnico;
- explicar claro;
- diagnosticar antes de vender;
- hacer preguntas inteligentes;
- detectar urgencia;
- llevar a llamada si hay fit;
- manejar objeciones;
- resumir valor de negocio;
- notificar al owner si el lead esta caliente.

No debe:

- inventar precios;
- inventar disponibilidad;
- prometer resultados garantizados;
- mentir con casos de exito;
- presionar de forma agresiva;
- enviar mensajes eternos;
- usar tono de bot generico.

## Flujo ideal

```text
lead escribe
|
mensaje entra a conversacion
|
router detecta sales_ai
|
LeadCreationService crea o actualiza lead
|
LeadScoringService calcula score
|
SalesConversationAgent genera respuesta
|
SafetyGuard revisa
|
WhatsApp envia
|
si score alto, NotificationService avisa al owner
|
si corresponde, TaskService crea seguimiento
```

## Endpoints

```text
GET   /api/v1/leads/
POST  /api/v1/leads/
GET   /api/v1/leads/{id}/
PATCH /api/v1/leads/{id}/

POST  /api/v1/leads/{id}/score/
POST  /api/v1/leads/{id}/convert-to-client/
POST  /api/v1/leads/{id}/mark-lost/
POST  /api/v1/leads/{id}/schedule-followup/

GET   /api/v1/sales/opportunities/
POST  /api/v1/sales/opportunities/

GET   /api/v1/sales/call-requests/
POST  /api/v1/sales/call-requests/{id}/mark-scheduled/
```

## Workers

- `leads.score_lead_from_conversation`;
- `leads.detect_hot_lead`;
- `sales.generate_sales_reply`;
- `sales.handle_objection`;
- `sales.create_followup_task`;
- `sales.notify_owner_for_hot_lead`.

## Tests obligatorios

- `test_unknown_contact_becomes_lead`;
- `test_lead_score_calculation`;
- `test_hot_lead_triggers_notification`;
- `test_sales_agent_does_not_invent_price`;
- `test_sales_agent_asks_diagnostic_question`;
- `test_sales_agent_creates_call_request`;
- `test_objection_price_handling`;
- `test_lead_stage_history_created`;
- `test_lead_convert_to_client`;
- `test_unqualified_lead_detection`.

## Criterios de perfeccion

La fase 6 esta perfecta cuando:

1. Un desconocido puede convertirse en lead automaticamente.
2. Cada lead tiene score.
3. Cada score tiene explicacion.
4. El score se versiona en snapshots.
5. El agente vendedor responde con tono definido.
6. El agente no inventa informacion.
7. El agente maneja objeciones.
8. El agente busca llevar a llamada.
9. Los leads calientes notifican al owner.
10. Se crean tareas de seguimiento.
11. Hay historial de etapas.
12. Hay conversion lead a cliente.
13. Hay tests de calidad comercial.
14. Hay guardrails de venta.
15. Todo queda auditado.

## Riesgos a evitar

- que la IA decida score final sin reglas;
- responder precios sin SalesPolicy;
- convertir clientes existentes en leads;
- no guardar historial de stage;
- crear tareas duplicadas;
- generar mensajes largos o agresivos;
- enviar respuesta sin SafetyGuard.

## Recomendacion de division en subfases

### Fase 6.1: Modelo de lead y pipeline

Entregables:

- Lead;
- LeadStageHistory;
- LeadSource;
- endpoints CRUD;
- filtros por stage/temperature.

Validacion:

- tests de creacion;
- tests de cambio de stage;
- tests de historial.

### Fase 6.2: Lead creation desde conversacion

Entregables:

- LeadCreationService;
- integration con ConversationRouter;
- unknown contact to lead;
- eventos internos.

Validacion:

- desconocido se vuelve lead;
- cliente no se vuelve lead;
- deduplicacion por contact_id.

### Fase 6.3: Scoring deterministico + IA

Entregables:

- LeadScoringService;
- scoring factors;
- AI structured output;
- snapshots.

Validacion:

- score reproducible;
- output invalido no actualiza;
- snapshot creado.

### Fase 6.4: Sales agent basico

Entregables:

- contexto comercial;
- prompt sales_agent;
- SalesReplyPolicy;
- SafetyGuard;
- envio por WhatsApp.

Validacion:

- no inventa precio;
- hace pregunta diagnostica;
- respuesta queda guardada.

### Fase 6.5: Objeciones y llamadas

Entregables:

- SalesObjection;
- SalesCallRequest;
- CallCloser;
- followup tasks.

Validacion:

- objecion de precio manejada;
- quiere llamada crea call request;
- se notifica owner.

### Fase 6.6: Conversion y reporting base

Entregables:

- convert-to-client;
- mark-lost;
- OpportunityService;
- eventos analytics base.

Validacion:

- lead won crea cliente;
- lost registra razon;
- pipeline queda consultable.
