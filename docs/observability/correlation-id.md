# Correlation ID

`RequestIDMiddleware` garantiza:

- `X-Request-ID` en request/response;
- `X-Correlation-ID` en request/response;
- reemplazo de headers invalidos;
- contexto disponible para logs, audit y Celery.

Flujo:

```mermaid
flowchart LR
  A["HTTP request"] --> B["RequestIDMiddleware"]
  B --> C["resolve_current_organization"]
  C --> D["service/domain logic"]
  D --> E["Celery task headers"]
  E --> F["worker context"]
  F --> G["logs + audit + analytics"]
```

Los workers propagan el contexto con headers Celery bajo `observability_context`.
