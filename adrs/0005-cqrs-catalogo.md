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

- **Un solo modelo de lecturas/escrituras** — más simple, pero no cumple el patrón obligatorio y
  dificulta cachear la búsqueda bajo 250 usuarios concurrentes.

## Consecuencias

- Lecturas rápidas y cacheables sin bloquear escrituras; alta/edición aislada y transaccional.
- Trade-off: dos caminos de datos (lectura vs escritura) que deben mantenerse sincronizados; la
  indexación en Meilisearch introduce eventual consistencia entre la DB y el índice de búsqueda.
