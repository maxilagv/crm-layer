# Implementacion Fase 6

## Alcance

Se agregan `crm.leads` y `crm.sales` siguiendo el monolito modular existente
(`apps/api/src/crm/<modulo>`). No se usa `crm/modules` porque el repositorio
real no sigue esa ruta.

## Modulos

Leads:

- modelos `Lead`, `LeadScoreSnapshot`, `LeadStageHistory`, `LeadSource`;
- dominio con enums, reglas y eventos;
- services de creacion, scoring, lifecycle, followup, conversion y
  qualification;
- selectors de lista, detalle, metricas y pipeline;
- endpoints DRF;
- workers Celery;
- comandos operativos.

Sales:

- modelos `SalesOpportunity`, `SalesFollowup`, `SalesObjection`,
  `SalesPlaybook`, `SalesCallRequest`;
- services de agente vendedor, policy, objeciones, call closer, oportunidades,
  followups y playbooks;
- selectors;
- endpoints DRF;
- workers Celery;
- comandos operativos.

## IA

`leads` y `sales` no importan providers ni SDKs. La unica interfaz de IA usada
es `AIGateway`:

- `AIGateway.score_lead()`;
- `AIGateway.generate_sales_reply()`.

El score final lo calcula backend con pesos deterministas. La salida de IA solo
aporta señales estructuradas. Si la salida IA es invalida, no se actualiza el
lead y no se crea snapshot.

## Seguridad comercial

`SalesReplyPolicy` complementa `SafetyGuard` y bloquea:

- precios sin politica autorizada;
- promesas garantizadas;
- disponibilidad no provista;
- lenguaje agresivo;
- casos de exito no configurados;
- datos sensibles;
- cierre de contrato/pago sin humano;
- respuesta que ignora objecion de precio.

## Integraciones pendientes

No existe todavia modulo global de `tasks` ni `notifications`. La fase implementa:

- `SalesFollowup` como tarea comercial idempotente;
- outbox `sales.hot_lead_owner_notification.v1` para notificar owner.

Cuando esas fases existan, consumiran estos eventos sin cambiar el dominio.

## Validacion

Ejecutado correctamente:

```bash
ruff check .
ruff format --check src/crm/leads src/crm/sales tests/api/test_phase6_leads_sales.py tests/factories/leads.py tests/factories/sales.py
python manage.py check --settings=crm.config.settings.test
python manage.py makemigrations --check --dry-run --settings=crm.config.settings.test
python manage.py spectacular --file ../../docs/api/openapi.yaml --settings=crm.config.settings.test
DATABASE_URL=sqlite:///.../.tmp-phase6.sqlite3 python manage.py migrate --settings=crm.config.settings.test --noinput
DATABASE_URL=sqlite:///.../.tmp-phase6.sqlite3 pytest tests/api/test_phase6_leads_sales.py -q
```

Resultados:

- tests fase 6: `19 passed`;
- suite completa con SQLite temporal: `217 passed`, `1 failed` porque
  `tests/unit/test_settings.py::test_tests_run_against_postgres` exige
  PostgreSQL por diseno;
- OpenAPI: 0 errores, warnings de nombres de enums;
- `ruff format --check .` global sigue mostrando 16 archivos preexistentes fuera
  de fase 6 que requieren formato.

Bloqueo de entorno:

```text
postgres://ai_crm:ai_crm@localhost:5432/ai_crm
```

La suite normal no puede crear la base de test porque PostgreSQL local rechaza
esas credenciales. La implementacion queda validada funcionalmente con SQLite
temporal y lista para correr contra PostgreSQL cuando se corrija el entorno.
