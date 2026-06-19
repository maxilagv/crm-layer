# AI Cost Spike

Severidad: medium

Senal:

- `ai_cost_total >= 25` USD/dia por organizacion.

Acciones:

1. Revisar `/api/v1/analytics/ai-costs/`.
2. Agrupar por provider/model/purpose.
3. Revisar loops de workers o automatizaciones.
4. Aplicar limites temporales por purpose.
5. Ajustar modelos en `AIModelConfig`.
