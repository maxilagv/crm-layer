# Roadmap del Agente — Camino al "Top 10"

> Objetivo: llevar el agente de un bot de WhatsApp muy bueno a un **asistente de
> trabajo de élite**, que entiende, recuerda, **produce entregables casi
> perfectos** y actúa con proactividad **bajo control humano**.
>
> Este documento organiza las mejoras en fases incrementales. Cada fase apoya en
> lo ya construido y respeta los principios del proyecto (ver abajo). Las fases
> son secuenciables pero algunas se pueden paralelizar.

---

## Estado actual (base sobre la que construimos)

Ya funciona y está testeado:

- **Inbox WhatsApp** (puente no oficial por QR, temporal) ↔ **IA** end-to-end.
- **3 modos de agente**: ventas (`sales_reply`), soporte (`support_reply`) y
  **asistente personal del dueño** (`assistant_reply`, ruteado por número de owner).
- **Audios entrantes**: descarga + transcripción + respuesta.
- **Proveedor Gemini** (vía endpoint OpenAI-compat) + OpenAI/Anthropic/Fake.
- **Prompts versionados** por propósito (system/developer/schema/examples) con
  activación/archivado auditados.
- **Framework de tools**: `create_task`, `create_ticket`, `create_call_request`,
  `update_lead`, `notify_owner`, `generate_image`, `send_whatsapp_message`,
  `pause_conversation_ai` (con niveles de riesgo + política de permisos).
- **Módulos CRM**: contactos, leads, clientes, soporte/tickets, tareas, media
  (almacenamiento privado + URLs firmadas), analítica, configuración.
- **Plataforma**: AIGateway único, ContextBuilder, SafetyGuard, AIRuns +
  auditoría, outbox transaccional, workers Celery, multi-tenant (`organization_id`).

## Principios (no negociables en todas las fases)

1. **Control humano sobre lo sensible**: enviar propuestas, cotizar, cobrar o
   prometer se hace en **modo borrador / aprobación**, nunca a ciegas.
2. **IA solo vía `AIGateway`**; sin SDKs de proveedor fuera de `crm/ai/providers/`.
3. **Trazabilidad total**: todo pasa por AIRun + auditoría; siempre se puede
   responder "¿por qué hizo esto?".
4. **Privacidad**: archivos privados por defecto (signed URLs), secretos en el
   entorno, sin filtrar datos entre organizaciones.
5. **Todo con tests**: ninguna fase se cierra sin tests + verificación.
6. **No romper fases anteriores.** Multi-tenant desde el día uno (listo para SaaS).

---

## Resumen de fases

| Fase | Tema | Valor | Esfuerzo |
|------|------|-------|----------|
| **8** | Motor de documentos (Brand Kit + PDF/Excel/PPT) | ⭐⭐⭐⭐⭐ | 🔴 alto |
| **9** | Memoria y conocimiento (RAG + estilo del negocio) | ⭐⭐⭐⭐⭐ | 🔴 alto |
| **10** | Proactividad y autonomía con control | ⭐⭐⭐⭐ | 🟡 medio |
| **11** | Multimodal completo (visión, docs entrantes, voz) | ⭐⭐⭐⭐ | 🟡 medio |
| **12** | Integraciones (Calendar, cobros, GitHub/Linear, mail) | ⭐⭐⭐⭐ | 🟡 medio |
| **13** | Inteligencia comercial + experiencia del agente | ⭐⭐⭐ | 🟡 medio |
| **14** | Cazador outbound autónomo | ⭐⭐⭐⭐ | 🔴 alto |

Leyenda esfuerzo por ítem: 🟢 quick win · 🟡 medio · 🔴 lift grande.

---

## Fase 8 — Motor de documentos ("entregables casi perfectos")

**Objetivo:** que el agente genere PDF, Excel y PowerPoint **con tu marca y datos
reales del CRM**, con preview + aprobación antes de enviar. La diferencia entre
"genera un PDF" y "genera un PDF perfecto" es el **sistema de plantillas + Brand
Kit + datos vivos + revisión humana**.

> **Estado (2026-06-13): ✅ IMPLEMENTADA.** App `crm.documents` (BrandKit +
> GeneratedDocument), un payload normalizado → 3 renderers branded (reportlab/
> openpyxl/python-pptx), API `/api/v1/documents/`, tool del agente, propósito de
> IA `DOCUMENT_DRAFT` (Gemini-friendly), comando `/propuesta` (+`/presupuesto`,
> `/excel`, `/deck`, `/informe`) en el puente WhatsApp con envío del archivo, y en
> el panel: biblioteca de **Documentos** + página **Kit de marca**. Verificado:
> suite backend completa verde + typecheck/lint/build FE. Se usó `reportlab` (no
> `weasyprint`) por ser pure-python y portable en Windows.

### 8.1 Brand Kit + motor de plantillas 🔴 (base de todo)
- Modelo `BrandKit` por organización: logo, paleta, tipografías, datos fiscales,
  pie de página, T&C por defecto, tono.
- Motor de render por plantilla (datos → documento) reutilizable para PDF/Excel/PPT.
- Plantillas versionadas (como los prompts): editar sin romper las activas.
- Salida → **MediaAsset privado** (ya existe) + signed URL para enviar/descargar.
- **Criterios:** un mismo dato del CRM produce el mismo doc on-brand de forma
  determinista; preview antes de finalizar.

### 8.2 PDF 🟡
- Tipos: **presupuesto/cotización**, **propuesta comercial**, **SOW/contrato**,
  **factura/recibo**, **informe de avance** (sprint/proyecto), one-pager.
- Tabla de ítems, subtotales/impuestos/total, numeración, lugar de firma, T&C.
- Tool nuevo `generate_pdf` (riesgo medio → requiere aprobación para enviar).
- **Criterios:** PDF abre bien, on-brand, montos correctos desde datos del CRM.

### 8.3 Excel 🟢
- Export de leads/clientes/tickets/tareas filtrados.
- **Modelo de costos/horas** de proyecto con fórmulas vivas; presupuesto editable.
- Cronograma/Gantt simple.
- Tool `generate_spreadsheet` (openpyxl) → MediaAsset.

### 8.4 PowerPoint 🔴
- **Pitch deck** / propuesta visual con estructura probada: problema → solución →
  alcance → hitos → precio → timeline → por qué nosotros.
- Plantilla de marca + gráficos a partir de datos.
- Tool `generate_deck` (python-pptx).

### 8.5 Flujo de uso (UX) 🟡
- Comando por WhatsApp: `/propuesta <cliente>`, `/presupuesto`, `/informe`.
- El agente arma → **preview** (link) → vos aprobás → se envía.
- Pantalla en el panel: biblioteca de documentos generados + plantillas.

**Depende de:** 8.1 antes que 8.2–8.5. **Dependencias técnicas:** `reportlab`/
`weasyprint` (PDF), `openpyxl` (Excel), `python-pptx` (PPT); todo encaja con el
módulo `media` (privado + signed URLs) y el framework de tools.

---

## Fase 9 — Memoria y conocimiento

**Objetivo:** que el agente recuerde y **suene a vos**, y responda con material
real en vez de inventar.

> **Estado (2026-06-16): 9.1, 9.2 y 9.4 ✅ IMPLEMENTADAS.** Memoria de largo plazo
> por contacto (propósito `MEMORY_EXTRACTION` + persistencia + recuperación
> selectiva inyectada en ventas/soporte + task `extract_conversation_memory` +
> comando `backfill_memories`); estilo del owner (campos en BusinessProfile +
> `owner_voice` inyectado en ventas/soporte/propuestas, editable en Config ›
> Perfil de negocio); briefs automáticos (propósito `PROJECT_BRIEF` + endpoint
> `POST /api/v1/ai/project-briefs/`). Verificado: 388 tests backend verdes,
> typecheck/lint FE. **9.3 (RAG / base de conocimiento) queda pendiente** como
> próximo paso (la infra — `AIEmbedding`, `create_embedding`, pgvector — ya está).

### 9.1 Memoria de largo plazo por contacto/cliente 🟡
- Potenciar `ConversationMemory`: preferencias, decisiones, compromisos, historia.
- Recuperación selectiva en el `ContextBuilder` (sin inflar el prompt).

### 9.2 Memoria del negocio / estilo del owner 🟡
- Capturar tu forma de redactar, precios, criterios → el agente **clona tu estilo**.
- Editable desde Configuración.

### 9.3 Base de conocimiento (RAG) 🔴
- Cargar documentos (propuestas pasadas, casos de éxito, specs, FAQs).
- Embeddings + recuperación; el agente responde/cotiza **citando** fuentes.
- Reusa `AIGateway.create_embedding` (ya existe) + pgvector.

### 9.4 Briefs automáticos 🟢
- De una charla, el agente arma un brief de proyecto listo para desarrollo.

**Depende de:** independiente de la Fase 8; 9.3 habilita propuestas mucho mejores.

---

## Fase 10 — Proactividad y autonomía (con freno de mano)

**Objetivo:** que el agente trabaje **solo** en lo seguro y te **avise/proponga**
en lo importante.

### 10.1 Follow-ups automáticos 🟡
- Lead frío X días → reactivación; cliente sin contacto → check-in; "te mando el
  viernes" → recordatorio/envío programado. (Worker Celery + reglas.)

### 10.2 Resumen proactivo diario/semanal al owner 🟢
- "Hoy: N leads nuevos, M pendientes, respondé esto primero". Por WhatsApp.

### 10.3 Detección de oportunidades y riesgos 🟡
- Lead caliente, upsell, **sentimiento negativo / riesgo de churn** → aviso al owner.

### 10.4 Auto-triage de la bandeja 🟢
- Prioriza, etiqueta y propone próxima acción por conversación.

### 10.5 Modo borrador / aprobación humana 🟢 (transversal, crítico)
- Acciones sensibles quedan como **propuesta** que confirmás con un toque.
- Refuerza el principio #1; aplica a Fase 8 (envíos) y Fase 12 (cobros).

**Depende de:** workers (ya), SafetyGuard (ya). 10.5 conviene hacerlo temprano.

---

## Fase 11 — Multimodal completo

**Objetivo:** que entienda y produzca en todos los formatos.

### 11.1 Visión (imágenes/capturas entrantes) 🟡
- Cliente manda screenshot de un error → el agente lo interpreta y crea el ticket.
- El puente ya descarga media; sumar análisis de imagen vía gateway (modelo con visión).

### 11.2 Documentos entrantes (PDF/Excel) 🟡
- Te mandan un PDF/planilla → el agente lo lee y extrae datos (alcance, montos).

### 11.3 Responder con audio (TTS) 🟡
- Opción de que el agente conteste con nota de voz, no solo texto.

**Depende de:** modelos con capacidad de visión/audio en el proveedor activo
(OpenAI para imagen/voz; Gemini para visión de texto/imagen según modelo).

---

## Fase 12 — Integraciones (el agente como hub operativo)

**Objetivo:** que cierre el círculo con tus herramientas. Cada integración = un
tool nuevo + credenciales (OAuth/API).

### 12.1 Google Calendar 🟡
- Agendar reuniones/demos desde la charla; ver disponibilidad.

### 12.2 Links de cobro 🟡
- Mercado Pago / Stripe → genera link de seña/pago (con aprobación, Fase 10.5).

### 12.3 GitHub / Linear 🟡 (clave para un estudio de software)
- Convierte un pedido del cliente en issue/tarea de desarrollo.

### 12.4 Gmail / Sheets / e-sign 🟡
- Enviar por mail, exportar a Sheets, firmar propuestas.

**Depende de:** credenciales externas (Google Cloud, MP/Stripe, GitHub). Encaja
con el framework de tools + almacenamiento cifrado de credenciales por-org
(necesario al pasar a SaaS).

---

## Fase 13 — Inteligencia comercial/soporte + experiencia

**Objetivo:** afinar conversión, calidad y la experiencia de operarlo.

- **Copiloto en el inbox** 🟢: sugiere la respuesta; enviás con un toque.
- **Next-best-action por lead** 🟡 + scoring (base existente).
- **A/B de mensajes** 🔴: aprende qué texto convierte.
- **Comandos rápidos** 🟢: `/resumen`, `/agenda`, `/cobrar`, `/propuesta`.
- **Onboarding conversacional** 🟡: el agente te entrevista y autoconfigura el
  perfil de negocio.
- **Multi-idioma** 🟢.

---

## Fase 14 — Cazador

**Objetivo:** que el CRM descubra negocios locales, los califique con IA, prepare
un primer contacto respetuoso por WhatsApp y eleve al pipeline solo las respuestas
con interés real.

> **Estado (2026-06-17): 14.1 a 14.7 implementadas + pulido operativo.** Existe
> `crm.prospecting` con campañas/prospectos, discovery vía Google Places, tres
> propósitos de IA (`PROSPECT_QUALIFICATION`, `OUTREACH_OPENER`, `REPLY_INTENT`),
> cola saliente pull para el bridge WhatsApp, orquestación con guardarraíles,
> interpretación de respuestas y módulo web **Cazador** (Campañas + Prospectos).
> El descubrimiento y la salida se disparan desde la UI (`POST .../discover/` y
> `POST .../run-outreach/`, gateadas por `PROSPECTING_MANAGE`), y cada prospecto
> descubierto encola su calificación en `transaction.on_commit`.

### Flujo operativo

1. **Descubrimiento:** una campaña consulta Google Places (botón "Buscar" →
   `POST /api/v1/prospecting/campaigns/<id>/discover/`) y crea `Prospect`
   deduplicado por organización + campaña + `place_id`.
2. **Calificación:** al crear el `Prospect` se encola `qualify_prospect` en
   `on_commit`; `ProspectQualificationService` llama al AIGateway y setea
   `fit_score`, `signals`, `reasoning`, `recommended_angle` y `ai_run_id`.
3. **Revisión/contacto:** el owner aprueba manualmente, o `auto_contact` permite
   contactar calificados que superan `min_fit_score` (botón "Contactar" →
   `POST /api/v1/prospecting/campaigns/<id>/run-outreach/`).
4. **Salida WhatsApp:** `ProspectOutreachService` genera opener con voz del owner
   y encola `whatsapp.OutboundMessage`; el bridge hace polling y reporta delivery.
5. **Respuesta:** el inbound asociado al prospecto corre `REPLY_INTENT`; solo
   `interested` crea/asegura Lead y notifica al owner. Un prospecto con opt-out
   (keyword o `do_not_contact`) no recibe respuesta autónoma en ese mismo turno.

### Guardarraíles

- Campaña no activa o pausada: no envía.
- Tope diario por campaña usando `OutboundMessage` creado hoy.
- Horario hábil + jitter por `available_at`; el bridge no ve mensajes antes.
- Dedup por `prospect_id`, `contacted_at` e `idempotency_key`.
- Opt-out por keywords (`no`, `baja`, `no me escriban`, etc.) => `DO_NOT_CONTACT`
  y supresión del contacto.
- Lista de no-contactar por `campaign.metadata.do_not_contact_phones`.

### Decisiones y brechas

- **Memoria 9.1:** ahora se dispara automáticamente cada 6 inbound de una
  conversación, vía `transaction.on_commit`, solo si la org tiene provider/config
  y prompt activo para `MEMORY_EXTRACTION`. Si falla, no bloquea el puente.
- **Prompts enriquecidos:** ya existe comando de adopción para orgs existentes:
  `python manage.py ai_seed_prompts --update` (usar `--no-activate` para dejar
  drafts). No hizo falta agregar otro comando.
- **Gemini y documentos:** el tool `generate_document` sigue dependiendo de
  tool-calling; en Gemini se usa `/propuesta` o la API `DOCUMENT_DRAFT`.
- **Google Places:** el cliente sigue en endpoints legacy. La paginación corta
  con gracia si `next_page_token` falla; migrar a Places API (New) v1 con field
  masks queda como mejora cuando hagan falta más cuota/campos.
- **RAG 9.3:** sigue pendiente. La infraestructura (`AIEmbedding`,
  `AIGateway.create_embedding`, pgvector instalado) queda lista para retrieval.
- **Momento Contact/Lead:** el `Prospect` crea/guarda `contact_id` y
  `conversation_id` al encolar outreach. `lead_id` se guarda solo cuando la
  respuesta se clasifica como `interested`.

### Operatividad (pulido 2026-06-17)

Para que el sistema funcione end-to-end como asistente (recordatorios incluidos):

- **Worker con todas las colas:** el comando del worker en `docker-compose.*.yml`
  declara `-Q celery,ai_fast,ai_slow,...,operations,notifications,automations,...`.
  Sin esto `tasks.send_due_reminders` (ruteada a `operations`) nunca corría y los
  recordatorios no llegaban.
- **`OWNER_WHATSAPP_NUMBER`:** ahora se carga en settings; es el fallback para
  notificaciones/recordatorios del owner por WhatsApp cuando no hay
  `BusinessProfile.owner_phone`.
- **Outbox tolerante:** un evento sin handler registrado es no-op exitoso (no
  cae en dead-letter). Solo las excepciones de un handler reintenta/fallan.
- **Quickstart:** `make quickstart` (o `python manage.py quickstart`) deja una
  instancia usable: owner + organización, Gemini, prompts sembrados y perfil de
  negocio con teléfono del owner. Idempotente.
- **Disparadores de prospecting:** endpoints `discover/` y `run-outreach/` para
  no depender solo de Celery beat; el descubrimiento encadena la calificación.

---

## Qué lo vuelve "Top 10" (no es un feature suelto)

La élite surge de la **combinación**: entregables perfectos (Fase 8) + memoria
real y estilo propio (Fase 9) + proactividad con control humano (Fase 10). Un
agente que **te entiende, te recuerda, te arma la propuesta solo y te la deja
lista para aprobar** es de clase mundial.

### Sprint recomendado para arrancar
1. **8.1 Brand Kit + motor de plantillas** (desbloquea todos los docs).
2. **8.2 PDF de propuesta/presupuesto** con datos del CRM + preview/aprobación.
3. **8.3 Excel** (export + modelo de costos).
4. **10.5 Modo borrador/aprobación** (transversal, habilita envíos seguros).
5. **9.2 Memoria del negocio/estilo** (para que los docs y respuestas suenen a vos).
6. **8.4 PowerPoint** (pitch deck).

> Próximo paso sugerido: abrir **Fase 8** como `fase8.readme.md` con el detalle de
> implementación (modelos, tools, endpoints, plantillas, tests), al estilo de las
> fases anteriores.
