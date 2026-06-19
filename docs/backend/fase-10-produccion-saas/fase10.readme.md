# Fase 10: Produccion, backups, escalabilidad y preparacion SaaS

## Objetivo

Llevar el backend a produccion real. Esta fase incluye deploy, hardening, backups, restore, performance, colas separadas, seguridad operativa y preparacion para venderlo como SaaS.

Esta fase define si el sistema es un proyecto personal o una plataforma seria.

## Resultado esperado

Al terminar esta fase el backend debe poder:

- desplegarse de forma reproducible;
- tener staging y production;
- correr CI/CD;
- ejecutar migraciones controladas;
- hacer rollback;
- hacer backups automaticos;
- probar restore;
- separar workers por cola;
- operar con HTTPS;
- proteger secrets;
- usar storage privado;
- exponer health checks reales;
- tener alertas;
- medir uso por organizacion;
- soportar crecimiento futuro.

## Modulos involucrados

- `infra`
- `core`
- `billing`
- `integrations`
- `security`
- todos los modulos

## Servicios de produccion

En produccion inicial:

- `api`;
- `worker-default`;
- `worker-webhooks`;
- `worker-whatsapp`;
- `worker-ai-fast`;
- `worker-ai-slow`;
- `worker-media`;
- `worker-notifications`;
- `scheduler`;
- `postgres`;
- `redis`;
- `caddy/nginx`.

## Colas

Colas recomendadas:

- `default`;
- `webhooks`;
- `whatsapp_inbound`;
- `whatsapp_outbound`;
- `ai_fast`;
- `ai_slow`;
- `media`;
- `transcription`;
- `image_generation`;
- `notifications`;
- `scheduled_tasks`;
- `analytics`;
- `maintenance`.

Separacion importante:

- un audio no debe bloquear una venta;
- una imagen no debe bloquear una notificacion;
- un fallo de IA no debe tumbar WhatsApp;
- un webhook debe responder rapido aunque los workers esten lentos.

## Deploy

Flujo ideal:

```text
build image
|
run tests
|
run migrations check
|
deploy staging
|
smoke test staging
|
manual approval
|
deploy production
|
run migrations
|
restart api
|
restart workers
|
health check
|
smoke test production
```

## CI/CD

Workflows:

- `ci.yml`;
- `backend.yml`;
- `contracts.yml`;
- `security.yml`;
- `docker-build.yml`;
- `deploy-staging.yml`;
- `deploy-production.yml`.

Pipeline minimo:

- install;
- lint;
- format check;
- type/static checks;
- test;
- coverage;
- build;
- OpenAPI generation;
- Docker build;
- security scan;
- deploy staging;
- production approval;
- deploy production.

## Migraciones

Reglas:

- migraciones pequenas;
- migraciones reversibles cuando sea posible;
- backup antes de migraciones riesgosas;
- no hacer operaciones pesadas en request;
- no bloquear tablas grandes sin plan;
- separar schema migration y data migration si conviene;
- probar migracion en staging.

## Backups

Debe existir backup de:

- PostgreSQL;
- media assets;
- prompts activos;
- settings criticos;
- variables documentadas.

Retencion recomendada:

- ultimos 7 dias diarios;
- ultimas 4 semanas semanales;
- ultimos 6 meses mensuales.

Lo mas importante: probar restore.

Runbooks:

- `restore-database.md`;
- `restore-media.md`;
- `rotate-secrets.md`;
- `rollback-deploy.md`;
- `recover-worker-failure.md`;
- `recover-whatsapp-webhook.md`;
- `recover-ai-provider-outage.md`.

## Seguridad de produccion

Controles minimos:

- HTTPS obligatorio;
- secrets fuera del repo;
- API keys cifradas o hasheadas segun uso;
- webhooks validados;
- rate limits;
- CORS estricto;
- CSRF donde aplique;
- permisos por organizacion;
- logs sin secretos;
- backups cifrados;
- auditoria;
- soft delete;
- retencion de datos;
- proteccion contra replay;
- idempotencia;
- validacion de archivos;
- signed URLs temporales.

## Proteccion de archivos

Cada archivo debe tener:

- owner;
- `organization_id`;
- MIME type validado;
- size limit;
- checksum;
- storage privado;
- signed URL temporal;
- retention policy.

## Performance

Indices importantes:

- `contacts_contact_phone.phone_e164`;
- `conversations_conversation.contact_id`;
- `conversations_conversation.last_message_at`;
- `conversations_message.conversation_id`;
- `conversations_message.external_message_id`;
- `leads_lead.score`;
- `leads_lead.stage`;
- `support_ticket.status`;
- `support_ticket.priority`;
- `tasks_task.due_at`;
- `ai_ai_run.created_at`;
- `whatsapp_webhook_event.event_id`.

Optimizacion:

- `select_related`;
- `prefetch_related`;
- paginacion obligatoria;
- caching selectivo;
- bulk inserts;
- colas separadas;
- timeouts;
- retries;
- archivado de mensajes viejos.

## Preparacion SaaS

Aunque al principio sea privado, dejar listo:

- organizations;
- memberships;
- usage records;
- billing limits;
- plan configuration;
- feature flags;
- per-organization settings;
- per-organization AI costs;
- per-organization WhatsApp accounts.

Modulo billing inicial:

- `billing_plan`;
- `billing_subscription`;
- `billing_usage_record`;
- `billing_limit`.

Usage records:

- `messages_received`;
- `messages_sent`;
- `ai_tokens_used`;
- `ai_cost`;
- `audio_minutes`;
- `images_generated`;
- `storage_used`;
- `contacts_count`;
- `users_count`.

No hace falta cobrar todavia, pero si medir.

## Escalabilidad futura

### Etapa 1

- un VPS;
- Postgres local;
- Redis local;
- workers separados;
- storage externo;
- backups externos.

### Etapa 2

- Postgres en servidor separado;
- Redis separado;
- mas workers;
- mas colas;
- monitoring avanzado.

### Etapa 3

- extraer WhatsApp Gateway;
- extraer AI Gateway;
- read replicas;
- multi-node workers;
- multi-tenant real.

## Tests finales de produccion

Smoke tests:

- health;
- ready;
- login;
- crear contacto;
- crear conversacion;
- enviar mensaje simulado;
- worker procesa job;
- AI fake responde;
- OpenAPI disponible.

E2E critico:

```text
WhatsApp webhook simulado
|
contacto creado
|
conversacion creada
|
mensaje creado
|
lead creado
|
scoring ejecutado
|
respuesta generada
|
outbound message queued
```

## Criterios de perfeccion

La fase 10 esta perfecta cuando:

1. El deploy es reproducible.
2. Hay staging.
3. Hay produccion.
4. Hay CI/CD.
5. Hay migraciones controladas.
6. Hay rollback documentado.
7. Hay backups automaticos.
8. Hay restore probado.
9. Hay workers separados.
10. Hay colas separadas.
11. Hay health checks reales.
12. Hay alertas.
13. Hay logs utiles.
14. Hay seguridad de produccion.
15. Hay storage privado.
16. Hay indices principales.
17. Hay medicion de uso.
18. Hay preparacion SaaS.
19. El sistema puede recuperarse de fallos.
20. Se puede operar sin improvisar.

## Riesgos a evitar

- tener backups sin restore probado;
- correr todos los workers en una sola cola;
- desplegar sin staging;
- migrar tablas grandes sin plan;
- dejar CORS abierto;
- guardar media publica;
- no medir costos por organizacion;
- no tener rollback;
- depender de acciones manuales no documentadas.

## Recomendacion de division en subfases

### Fase 10.1: Staging reproducible

Entregables:

- servidor staging;
- deploy automatizado;
- env vars documentadas;
- smoke tests staging.

Validacion:

- deploy desde cero;
- health/ready;
- login;
- OpenAPI.

### Fase 10.2: CI/CD completo

Entregables:

- workflows de CI;
- docker build;
- security scan;
- deploy staging;
- approval para production.

Validacion:

- pipeline verde;
- build reproducible;
- deploy auditado.

### Fase 10.3: Workers y colas separadas

Entregables:

- routing Celery;
- workers por cola;
- concurrency por workload;
- monitoring de cola.

Validacion:

- audio no bloquea ventas;
- image_generation no bloquea notifications;
- webhook responde rapido.

### Fase 10.4: Backups y restore

Entregables:

- backup Postgres;
- backup media/settings/prompts;
- cifrado;
- retencion;
- runbook restore.

Validacion:

- restore en ambiente aislado;
- checksum;
- tiempo de recuperacion medido.

### Fase 10.5: Hardening de seguridad

Entregables:

- HTTPS;
- strict CORS/CSRF;
- rate limits;
- secrets management;
- signed URLs;
- validation de uploads;
- retention policy.

Validacion:

- tests de seguridad basicos;
- review de config prod;
- logs sin secretos.

### Fase 10.6: Performance e indices

Entregables:

- indices principales;
- query review;
- paginacion obligatoria;
- select_related/prefetch_related;
- archivado inicial.

Validacion:

- EXPLAIN en queries criticas;
- inbox rapido;
- messages paginados.

### Fase 10.7: SaaS readiness

Entregables:

- usage records;
- billing plan/subscription/limits base;
- feature flags;
- per-org AI costs;
- per-org WhatsApp accounts.

Validacion:

- consumo por organizacion;
- limites aplicables;
- dashboard de uso.

### Fase 10.8: Runbooks operativos

Entregables:

- rollback deploy;
- recover worker failure;
- recover webhook;
- recover AI outage;
- rotate secrets;
- restore DB/media.

Validacion:

- simulacro de fallo;
- runbook ejecutable;
- tiempos documentados.
