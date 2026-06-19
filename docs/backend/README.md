# Backend

Esta carpeta documenta como debe encararse el backend del CRM operativo.

El backend se construye como:

- modular monolith;
- event-driven interno;
- workers asincronos con Celery;
- AI Gateway abstraido;
- WhatsApp Gateway abstraido;
- PostgreSQL como fuente de verdad;
- auditoria completa;
- seguridad por diseno;
- preparacion SaaS desde el dia uno.

No se parte con microservicios. La decision base es construir un unico backend desplegable, pero organizado internamente como si cada modulo pudiera separarse en el futuro.

## Regla de autoridad

El backend es la autoridad absoluta sobre:

- usuarios;
- organizaciones;
- contactos;
- clientes;
- leads;
- conversaciones;
- mensajes;
- tickets;
- tareas;
- prompts;
- IA;
- WhatsApp;
- audios;
- imagenes;
- notificaciones;
- automatizaciones;
- auditoria;
- metricas;
- costos;
- seguridad.

Next.js consume APIs, muestra informacion, permite control manual y administra configuracion. No recibe webhooks criticos, no coordina workers y no ejecuta reglas de negocio centrales.

## Estructura conceptual objetivo

```text
Next.js Dashboard
        |
Django REST API
        |
Modulos de negocio
        |
PostgreSQL / Redis / Object Storage
        |
Workers Celery
        |
OpenAI / Anthropic / WhatsApp / Storage
```

## Estructura backend objetivo

La estructura ideal a medida que el backend madure es:

```text
apps/api/
|-- src/
|   \-- crm/
|       |-- config/
|       |-- core/
|       \-- modules/
|           |-- accounts/
|           |-- organizations/
|           |-- settings/
|           |-- contacts/
|           |-- conversations/
|           |-- whatsapp/
|           |-- ai/
|           |-- leads/
|           |-- sales/
|           |-- clients/
|           |-- support/
|           |-- media/
|           |-- tasks/
|           |-- notifications/
|           |-- automations/
|           |-- analytics/
|           |-- audit/
|           |-- integrations/
|           \-- billing/
|-- tests/
|-- manage.py
\-- pyproject.toml
```

El repo ya usa el layout `apps/api/src/crm/*` (config, core, integrations, audit). El scaffold legacy `apps/api/crm_core/*` fue eliminado en Fase 1; los modulos de negocio (whatsapp, conversations, leads, etc.) se crearan bajo `src/crm/` en sus fases correspondientes siguiendo estas reglas.

## Estructura interna obligatoria por modulo

Cada modulo debe tender a esta forma:

```text
crm/modules/<module>/
|-- __init__.py
|-- apps.py
|-- admin.py
|-- models.py
|-- migrations/
|-- api/
|   |-- serializers.py
|   |-- views.py
|   |-- urls.py
|   |-- filters.py
|   \-- permissions.py
|-- domain/
|   |-- enums.py
|   |-- events.py
|   |-- policies.py
|   |-- rules.py
|   \-- value_objects.py
|-- services/
|-- selectors/
|-- tasks.py
|-- signals.py
\-- tests/
```

## Regla de capas

- `api/`: entrada y salida HTTP.
- `models.py`: persistencia y relaciones.
- `services/`: mutaciones de negocio.
- `selectors/`: lecturas complejas.
- `domain/`: reglas puras, enums, value objects y eventos.
- `tasks.py`: trabajos asincronos.
- `tests/`: pruebas del modulo.

Las views no tienen logica de negocio. Validan input, llaman services/selectors y devuelven respuestas.

## Fases

1. [Fase 1: Fundacion tecnica](fase-01-fundacion-tecnica/fase1.readme.md)
2. [Fase 2: Seguridad, usuarios, organizaciones y settings](fase-02-seguridad-organizaciones-settings/fase2.readme.md)
3. [Fase 3: CRM core](fase-03-crm-core/fase3.readme.md)
4. [Fase 4: WhatsApp Gateway](fase-04-whatsapp-gateway/fase4.readme.md)
5. [Fase 5: AI Gateway](fase-05-ai-gateway/fase5.readme.md)
6. [Fase 6: Leads, scoring y agente vendedor](fase-06-leads-sales-agent/fase6.readme.md)
7. [Fase 7: Clientes, soporte, tickets, audios y media](fase-07-clientes-soporte-media/fase7.readme.md)
8. [Fase 8: Tareas, notificaciones y automatizaciones](fase-08-tareas-notificaciones-automatizaciones/fase8.readme.md)
9. [Fase 9: Analytics, auditoria, testing, evals y observabilidad](fase-09-analytics-auditoria-observabilidad/fase9.readme.md)
10. [Fase 10: Produccion, backups, escalabilidad y SaaS](fase-10-produccion-saas/fase10.readme.md)

## Orden recomendado de construccion

No conviene construir todo completo antes de probar. El orden recomendado es profundidad progresiva:

- primera entrega seria: fase 1 completa, fase 2 base, fase 3 completa, fase 4 inbound/outbound basico, fase 5 AI Gateway basico y fase 6 sales agent basico;
- segunda entrega: fase 7 soporte/audio y fase 8 tareas/notificaciones;
- tercera entrega: fase 9 calidad y fase 10 produccion robusta.

El estandar final del backend no es "un bot". Es un producto backend operable, trazable, recuperable y eventualmente vendible como SaaS.
