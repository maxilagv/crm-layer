# Fase 2: Seguridad, usuarios, organizaciones y configuracion del negocio

Documento de implementacion actual: [implementacion.md](implementacion.md).

## Objetivo

Construir la identidad del sistema: usuarios, roles, permisos, organizaciones y configuracion interna. Aunque inicialmente el CRM sea de uso privado, debe nacer como producto serio.

Esta fase define:

- quien puede entrar;
- que puede hacer;
- sobre que organizacion opera;
- que reglas comerciales tiene el negocio;
- que reglas de soporte existen;
- que comportamiento puede tener la IA;
- que queda auditado.

## Resultado esperado

Al terminar esta fase el backend debe poder:

- autenticar usuarios;
- resolver el usuario actual;
- resolver la organizacion actual;
- aislar datos por organizacion;
- aplicar roles y permisos;
- crear y revocar API keys;
- guardar configuracion comercial;
- guardar configuracion de soporte;
- guardar configuracion de IA;
- auditar eventos de seguridad y cambios de settings.

## Modulos involucrados

- `accounts`
- `organizations`
- `settings`
- `audit`
- `core.security`

## Usuarios

Modelo:

```text
accounts_user
```

Campos:

- `id`;
- `email`;
- `name`;
- `phone`;
- `password_hash`;
- `is_active`;
- `is_staff`;
- `is_superuser`;
- `last_login_at`;
- `timezone`;
- `locale`;
- `metadata`;
- `created_at`;
- `updated_at`.

Reglas:

- email unico;
- password nunca se guarda plano;
- usuario inactivo no puede autenticar;
- login fallido se audita;
- el sistema debe soportar timezone por usuario.

## Organizaciones

Modelo:

```text
organizations_organization
```

Campos:

- `id`;
- `name`;
- `slug`;
- `owner_id`;
- `status`;
- `plan`;
- `default_timezone`;
- `default_language`;
- `metadata`;
- `created_at`;
- `updated_at`.

Aunque al principio haya una sola organizacion, todo dato importante debe pertenecer a una. Esto evita rehacer el backend si despues el CRM se vende como SaaS.

## Memberships

Modelo:

```text
organizations_membership
```

Campos:

- `id`;
- `organization_id`;
- `user_id`;
- `role`;
- `status`;
- `joined_at`;
- `created_at`;
- `updated_at`.

Roles iniciales:

- `owner`;
- `admin`;
- `operator`;
- `viewer`;
- `ai_agent`;
- `system`.

## Permisos

Permisos por accion:

```text
contacts.view
contacts.create
contacts.update
conversations.view
conversations.reply
conversations.takeover
leads.view
leads.update
clients.view
tickets.manage
tasks.manage
prompts.manage
settings.manage
audit.view
```

No hace falta construir un RBAC excesivo al principio, pero si debe existir la estructura para preguntar de forma consistente:

```text
can(user, "conversations.reply", organization)
```

## Autenticacion

Endpoints:

```text
POST /api/v1/auth/login/
POST /api/v1/auth/logout/
POST /api/v1/auth/refresh/
GET  /api/v1/auth/me/
```

Debe incluir:

- rate limit de login;
- registro de intentos fallidos;
- tokens seguros o sesion segura;
- expiracion;
- refresh;
- logout real;
- auditoria.

`/auth/me/` es critico para Next.js. Debe devolver usuario, organizacion actual, roles, permisos y flags relevantes.

## API keys internas

Modelo:

```text
accounts_api_key
```

Campos:

- `id`;
- `organization_id`;
- `name`;
- `prefix`;
- `hashed_key`;
- `scopes`;
- `last_used_at`;
- `expires_at`;
- `revoked_at`;
- `created_by_id`;
- `created_at`.

Reglas:

- la key completa solo se muestra una vez;
- se guarda hash, nunca texto plano;
- se usa prefix para identificarla;
- scopes limitan permisos;
- `last_used_at` se actualiza;
- revocacion es soft revoke, no delete fisico.

## Configuracion del negocio

Modulo:

```text
settings
```

Modelos:

- `settings_business_profile`;
- `settings_sales_policy`;
- `settings_support_policy`;
- `settings_ai_behavior_policy`;
- `settings_notification_policy`;
- `settings_whatsapp_policy`.

La regla importante: las politicas criticas no deben estar hardcodeadas en prompts ni services. Deben vivir en base y ser editables desde el panel.

## BusinessProfile

Debe guardar:

- `business_name`;
- `owner_name`;
- `owner_phone`;
- `default_language`;
- `timezone`;
- `business_description`;
- `services_offered`;
- `target_clients`;
- `brand_tone`;
- `calendar_link`;
- `website_url`;
- `metadata`.

Este perfil alimenta agentes, respuestas, templates y notificaciones.

## SalesPolicy

Debe guardar:

- `main_sales_goal`;
- `call_to_action`;
- `can_quote_prices`;
- `price_min`;
- `price_max`;
- `price_policy_text`;
- `must_handoff_for_price`;
- `common_objections`;
- `forbidden_claims`;
- `sales_tone`;
- `metadata`.

Reglas iniciales:

- no inventar precios;
- no prometer resultados garantizados;
- no decir disponibilidad falsa;
- no cerrar contratos sin humano;
- intentar llevar a llamada cuando haya fit.

## SupportPolicy

Debe guardar:

- `support_hours`;
- `allowed_support_actions`;
- `forbidden_support_actions`;
- `urgent_keywords`;
- `critical_ticket_rules`;
- `data_request_policy`;
- `default_support_reply`;
- `metadata`.

Debe impedir que soporte pida passwords, tokens privados o informacion sensible innecesaria.

## AIBehaviorPolicy

Debe guardar:

- `default_provider`;
- `fallback_provider`;
- `default_sales_model`;
- `default_support_model`;
- `max_context_messages`;
- `temperature_sales`;
- `temperature_support`;
- `auto_reply_enabled`;
- `human_handoff_required_for_risks`;
- `metadata`.

Esta politica define cuando responde IA, con que modelo, con cuanto contexto y cuando debe derivar.

## Auditoria inicial

Eventos minimos:

- `user_login`;
- `user_logout`;
- `failed_login`;
- `api_key_created`;
- `api_key_revoked`;
- `settings_updated`;
- `permission_denied`.

Cada evento debe incluir:

- actor;
- organizacion;
- IP;
- user agent;
- request_id;
- recurso afectado;
- cambios relevantes.

## Endpoints

```text
GET   /api/v1/organizations/current/
PATCH /api/v1/organizations/current/

GET   /api/v1/users/
POST  /api/v1/users/
GET   /api/v1/users/{id}/
PATCH /api/v1/users/{id}/

GET   /api/v1/settings/business-profile/
PATCH /api/v1/settings/business-profile/

GET   /api/v1/settings/sales-policy/
PATCH /api/v1/settings/sales-policy/

GET   /api/v1/settings/support-policy/
PATCH /api/v1/settings/support-policy/

GET   /api/v1/settings/ai-policy/
PATCH /api/v1/settings/ai-policy/

POST   /api/v1/api-keys/
GET    /api/v1/api-keys/
DELETE /api/v1/api-keys/{id}/
```

## Tests obligatorios

- `test_login_success`;
- `test_login_failed_is_logged`;
- `test_auth_me`;
- `test_permission_denied`;
- `test_organization_data_isolation`;
- `test_api_key_is_hashed`;
- `test_business_profile_update`;
- `test_sales_policy_update`;
- `test_support_policy_update`;
- `test_settings_audit_log_created`.

## Criterios de perfeccion

La fase 2 esta perfecta cuando:

1. Todo usuario pertenece a una organizacion.
2. Todo recurso importante tiene `organization_id`.
3. Existen roles y permisos.
4. El login tiene rate limit.
5. Los intentos fallidos se auditan.
6. Las API keys se guardan hasheadas.
7. La configuracion comercial existe en base.
8. La configuracion de soporte existe en base.
9. La configuracion de IA existe en base.
10. Las reglas criticas no estan hardcodeadas.
11. El frontend puede consultar `/auth/me/`.
12. El backend puede saber si un usuario puede responder conversaciones.
13. Todo cambio de settings queda auditado.

## Riesgos a evitar

- construir sin organizacion por recurso;
- dejar roles como strings dispersos;
- guardar API keys en texto plano;
- permitir login sin rate limit;
- mezclar settings de negocio con variables de entorno;
- meter reglas comerciales dentro de prompts no versionados;
- no auditar cambios de politicas.

## Recomendacion de division en subfases

### Fase 2.1: Usuarios y autenticacion

Entregables:

- modelo user;
- login/logout/refresh/me;
- password hashing;
- rate limit;
- auditoria de login.

Validacion:

- tests de login correcto;
- tests de password incorrecta;
- tests de usuario inactivo;
- tests de auditoria.

### Fase 2.2: Organizaciones y membership

Entregables:

- modelo organization;
- modelo membership;
- resolver de organizacion actual;
- fixture o seed de organizacion default.

Validacion:

- test de usuario con organizacion;
- test de usuario sin acceso;
- test de aislamiento de datos.

### Fase 2.3: Permisos

Entregables:

- mapa de roles;
- mapa de permisos;
- helper `can`;
- permissions DRF;
- auditoria de denied.

Validacion:

- tests por rol;
- test de operator que puede responder;
- test de viewer que no puede mutar.

### Fase 2.4: API keys

Entregables:

- modelo API key;
- generacion con prefix;
- hash seguro;
- scopes;
- revocacion.

Validacion:

- test de key visible una vez;
- test de key hasheada;
- test de scope rechazado;
- test de revoked key.

### Fase 2.5: Settings de negocio

Entregables:

- BusinessProfile;
- SalesPolicy;
- SupportPolicy;
- AIBehaviorPolicy;
- NotificationPolicy;
- WhatsAppPolicy.

Validacion:

- tests de update;
- tests de permisos;
- tests de audit log.

### Fase 2.6: Contrato frontend

Entregables:

- serializers estables;
- endpoints listos para panel;
- OpenAPI actualizado;
- casos de error consistentes.

Validacion:

- schema generado;
- tests API;
- revision de contrato con web.
