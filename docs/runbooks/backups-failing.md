# Backups Failing

Severidad: critical

Senal:

- job de backup falla;
- ultimo backup supera RPO definido.

Acciones:

1. Verificar credenciales de object storage.
2. Verificar espacio local temporal.
3. Ejecutar backup manual.
4. Validar restauracion de una muestra.
5. No compactar audit/media hasta recuperar backups.
