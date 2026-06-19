# Gobierno de prompts

Cada prompt productivo debe tener:

- `key` estable;
- version incremental;
- objetivo;
- inputs permitidos;
- formato de salida esperado;
- reglas de seguridad;
- ejemplos de casos buenos y malos;
- criterios de evaluacion;
- owner.

Los cambios de prompt deben generar nueva `PromptVersion`, no editar historico.
