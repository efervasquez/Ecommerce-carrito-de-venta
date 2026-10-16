# ADR 0005: CQRS para el catálogo

## Estado

Aceptado

## Contexto

`AGENTS.md` §5 fija CQRS como patrón obligatorio: "separar lecturas de escrituras en el catálogo".
El catálogo tiene un perfil de carga asimétrico: muchas lecturas (búsqueda fuzzy, scroll infinito,
detalle de producto) y pocas escrituras (alta/edición de productos y stock, incluyendo el módulo de
contingencia manual).

## Decisión

Aplicar **CQRS al catálogo**: las lecturas (búsqueda, listado, detalle) se sirven desde un modelo
de lectura cacheable/denormalizable; las escrituras (alta, edición, stock, contingencia) pasan por
`Service -> Repository` transaccional. La indexación de búsqueda (Meilisearch) es el modelo de
lectura principal (ADR 0006).

## Alternativas consideradas

- **Vistas materializadas / Tablas denormalizadas en MySQL** — menor superficie operativa al no
  requerir un segundo servicio, pero no resuelve la tolerancia a typos en español ni el ranking de
  relevancia requerido por el PRD RF-02.1.
- **CQRS a nivel de código con Read-Replicas MySQL** — separa pools de lectura y escritura sin
  índice externo, pero duplicar instancias de MySQL sobrecarga memoria en hardware limitado
  (`AGENTS.md` §9) sin aportar búsqueda difusa.
- **Un solo modelo relacional de lecturas/escrituras en MySQL** — más simple, pero incumple el
  patrón mandatorio de `AGENTS.md` §5 y genera contención en la tabla de productos bajo 250
  usuarios concurrentes.

## Consecuencias

- Lecturas rápidas y cacheables sin bloquear escrituras; alta/edición aislada y transaccional.
- Trade-off: dos caminos de datos (lectura vs escritura) que deben mantenerse sincronizados; la
  indexación en Meilisearch introduce eventual consistencia entre la DB y el índice de búsqueda.
