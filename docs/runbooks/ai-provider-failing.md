# AI Provider Failing

Severidad: high

Senal:

- `ai_failures_total >= 3`;
- `AuditExternalRequest.success=false` para provider IA;
- `AIRun.status=failed`.

Acciones:

1. Revisar `AuditExternalRequest` filtrando por provider/model.
2. Confirmar variables de entorno del proveedor.
3. Activar fallback model/provider si existe.
4. Ejecutar evals con fake provider para descartar problema de prompt/schema.
5. Pausar automatizaciones si el fallo afecta respuestas al cliente.
