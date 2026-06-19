# PostgreSQL Disk Space

Severidad: critical

Senal:

- disco bajo;
- inserts fallando;
- migrations bloqueadas.

Acciones:

1. Verificar uso de disco en VPS.
2. Revisar tablas grandes: audit, messages, media, AI runs.
3. Confirmar backups antes de compactar.
4. Aplicar retencion audit con `audit.compact_old_logs` si hay politica definida.
5. Ampliar volumen si el crecimiento es real.
