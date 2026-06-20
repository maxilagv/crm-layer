# Backups

Backups automaticos quedan en este modulo. La estrategia inicial debe cubrir:

- dump diario de PostgreSQL;
- retencion local corta;
- copia cifrada a object storage externo;
- prueba periodica de restore;
- backup separado de media si el storage externo no versiona objetos.

