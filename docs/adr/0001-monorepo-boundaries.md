# ADR 0001: Monorepo con apps y packages

## Estado

Aceptado.

## Decision

Usamos un monorepo con `apps/web`, `apps/api`, `packages/*`, `infra`, `docs` y `scripts`.

## Motivo

El producto combina frontend, backend, contratos, workers e infraestructura. El monorepo permite evolucionar contratos y documentacion junto con la implementacion.

## Consecuencias

- TypeScript y Python conviven en el mismo repo.
- Los contratos compartidos viven en `packages/contracts`.
- La API sigue siendo la fuente de verdad del dominio.
