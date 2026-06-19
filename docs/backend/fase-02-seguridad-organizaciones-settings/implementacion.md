# Implementacion Fase 2

Este documento describe el estado implementado de la Fase 2 en el backend Django.
La fase deja lista la capa de identidad, organizaciones, permisos, API keys,
settings de negocio y auditoria basica para que el frontend Next.js pueda
operar el CRM sin tomar decisiones criticas de negocio.

## Modulos implementados

### accounts

Responsabilidades:

- usuario custom `accounts.User`;
- autenticacion JWT con refresh token y blacklist;
- login con rate limit por email e IP;
- logout con invalidacion de refresh token;
- endpoint `/api/v1/auth/me/`;
- gestion de usuarios por organizacion;
- API keys hasheadas, revocables, expirables y con scopes.

Decisiones:

- `AUTH_USER_MODEL = "accounts.User"`;
- el identificador de login es `email`;
- no se revelan diferencias entre usuario inexistente, password incorrecto o
  usuario inactivo;
- las API keys solo muestran el secreto una vez al crearse;
- las API keys se guardan con SHA-256 y se resuelven por prefijo.

### organizations

Responsabilidades:

- organizacion principal del tenant;
- membership usuario-organizacion;
- roles por membership;
- resolucion de organizacion actual;
- comando de bootstrap inicial.

Resolver de organizacion:

- primero usa `X-Organization-ID`;
- tambien acepta `organization_id` por query string para casos controlados;
- si el usuario tiene una sola membership activa, puede inferirla;
- si tiene multiples memberships activas, exige `X-Organization-ID`;
- si el usuario no pertenece a la organizacion pedida, responde `403`.

Comando de bootstrap:

```bash
python manage.py bootstrap_organization \
  --email owner@example.com \
  --name "Owner" \
  --organization "CRM Layer" \
  --password "change-me"
```

### core.security

Responsabilidades:

- roles centralizados;
- permisos centralizados;
- funcion `can(user, permission, organization)`;
- permiso DRF reutilizable `RequiresPermission`.

Roles actuales:

| Rol | Uso |
| --- | --- |
| `owner` | Control total de la organizacion. |
| `admin` | Gestion operativa completa sin ser superuser global. |
| `operator` | Trabajo diario: contactos, conversaciones, leads, tickets y tareas. |
| `viewer` | Lectura limitada. |
| `ai_agent` | Permisos acotados para ejecucion automatizada. |
| `system` | Reservado para procesos internos. |

Permisos actuales:

- `contacts.view`
- `contacts.create`
- `contacts.update`
- `conversations.view`
- `conversations.reply`
- `conversations.takeover`
- `leads.view`
- `leads.update`
- `clients.view`
- `tickets.manage`
- `tasks.manage`
- `prompts.manage`
- `settings.manage`
- `audit.view`

### business_settings

La app se llama `business_settings` para evitar conflicto conceptual y tecnico
con `crm.config.settings`.

Tablas implementadas:

- `settings_business_profile`;
- `settings_sales_policy`;
- `settings_support_policy`;
- `settings_ai_behavior_policy`;
- `settings_notification_policy`;
- `settings_whatsapp_policy`.

Cada tabla es por organizacion y se crea bajo demanda con `get_or_create`.
Los cambios se auditan con diff de campos modificados.

### audit

Responsabilidades implementadas:

- evento de auditoria para login exitoso;
- evento de auditoria para login fallido;
- evento de auditoria para permisos denegados;
- evento de auditoria para creacion/actualizacion de usuarios;
- evento de auditoria para creacion/revocacion de API keys;
- evento de auditoria para cambios de settings.

Los eventos guardan:

- `event_type`;
- `actor_id`;
- `organization_id`;
- `resource_type`;
- `resource_id`;
- `ip_address`;
- `user_agent`;
- `request_id`;
- `changes`;
- `metadata`.

## Endpoints implementados

Auth:

```text
POST /api/v1/auth/login/
POST /api/v1/auth/refresh/
POST /api/v1/auth/logout/
GET  /api/v1/auth/me/
```

Usuarios:

```text
GET   /api/v1/users/
POST  /api/v1/users/
GET   /api/v1/users/{user_id}/
PATCH /api/v1/users/{user_id}/
```

Organizacion:

```text
GET   /api/v1/organizations/current/
PATCH /api/v1/organizations/current/
```

API keys:

```text
GET    /api/v1/api-keys/
POST   /api/v1/api-keys/
DELETE /api/v1/api-keys/{api_key_id}/
```

Settings:

```text
GET   /api/v1/settings/business-profile/
PATCH /api/v1/settings/business-profile/
GET   /api/v1/settings/sales-policy/
PATCH /api/v1/settings/sales-policy/
GET   /api/v1/settings/support-policy/
PATCH /api/v1/settings/support-policy/
GET   /api/v1/settings/ai-policy/
PATCH /api/v1/settings/ai-policy/
GET   /api/v1/settings/notification-policy/
PATCH /api/v1/settings/notification-policy/
GET   /api/v1/settings/whatsapp-policy/
PATCH /api/v1/settings/whatsapp-policy/
```

## Autenticacion

JWT:

- access token corto;
- refresh token de 7 dias por defecto;
- refresh rotation activada;
- blacklist activada para logout y refresh rotation.

API keys:

- header recomendado: `X-API-Key`;
- formato generado: `acrm_{prefix}_{secret}`;
- el backend almacena solo `prefix` y `hashed_key`;
- una key debe estar activa, no expirada y no revocada;
- ademas del rol del usuario creador, la key debe tener el scope requerido por
  el endpoint.

## OpenAPI

El contrato se genera en:

```text
docs/api/openapi.yaml
```

Comando:

```bash
python manage.py spectacular --file ../../docs/api/openapi.yaml --settings=crm.config.settings.test
```

El schema declara:

- JWT Bearer auth;
- `X-API-Key` via `ApiKeyAuth`;
- endpoints de Fase 2;
- serializers de request/response para auth, usuarios, API keys, organizacion y
  settings.

## Tests agregados

Archivo:

```text
apps/api/tests/api/test_phase2_security.py
```

Cobertura:

- `test_login_success`;
- `test_login_failed_is_logged`;
- `test_auth_me`;
- `test_permission_denied_is_audited`;
- `test_organization_data_isolation`;
- `test_api_key_is_hashed_and_visible_once`;
- `test_api_key_scope_restricts_access`;
- `test_business_profile_update`;
- `test_sales_policy_update`;
- `test_support_policy_update`;
- `test_settings_audit_log_created`;
- `test_viewer_cannot_create_user`.

## Validacion local

Comandos ejecutados:

```bash
ruff check .
python manage.py check --settings=crm.config.settings.test
python manage.py makemigrations --check --dry-run --settings=crm.config.settings.test
pytest tests/api/test_phase2_security.py --collect-only -q
```

Estado:

- lint OK;
- Django system check OK;
- migraciones sin cambios pendientes;
- tests colectan correctamente;
- ejecucion completa de tests bloqueada en esta maquina porque PostgreSQL local
  rechaza las credenciales `ai_crm/ai_crm`.

Para ejecutar la suite completa, levantar un PostgreSQL compatible con:

```text
DATABASE_URL=postgres://ai_crm:ai_crm@localhost:5432/ai_crm
```

y luego correr:

```bash
pytest tests/api/test_phase2_security.py -q
```

## Criterio de cierre de Fase 2

La fase puede considerarse funcionalmente implementada cuando:

- las migraciones aplican en PostgreSQL;
- los tests de Fase 2 pasan completos;
- el frontend consume `/auth/me/` para conocer usuario, organizacion,
  membership, permisos y flags;
- todas las pantallas administrativas envian `X-Organization-ID`;
- ningun endpoint de mutacion de settings queda sin `settings.manage`;
- las API keys creadas desde el panel nunca vuelven a exponer el secreto.
