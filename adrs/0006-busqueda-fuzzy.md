# ADR 0006: Motor de búsqueda difusa (Meilisearch)

## Estado

Aceptado

## Contexto

El PRD RF-02.1 exige *Fuzzy Search* tolerante a errores de tipeo (ej. mapear "camiaa" → "camisa") y
renderizado en scroll infinito sin paginación. La búsqueda debe responder en <2.5 s bajo 250
usuarios concurrentes (RNF-01). La base es MySQL, cuyo `FULLTEXT` nativo no ofrece tolerancia real
a typos.

## Decisión

Usar **Meilisearch self-hosted** como motor de búsqueda e índice de lectura del catálogo, con
typo-tolerance configurable, ranking por relevancia y soporte de filtros (categoría, oferta,
precios bajos, requiere receta).

## Alternativas consideradas

- **MySQL FULLTEXT + n-gram** — sin servicios extra, pero la tolerancia a errores de tipeo es pobre
  y el ranking limitado; no cumple bien RF-02.1.
- **Elasticsearch** — potente y maduro, pero pesado en RAM; sobredimensionado y en contra de
  `AGENTS.md` §9 (optimización de memoria en hardware limitado).

## Consecuencias

- Búsqueda difusa de calidad con poco esfuerzo de integración y bajo consumo relativo de recursos.
- Trade-off: un servicio local adicional a mantener, y eventual consistencia entre MySQL y el
  índice (requiere sincronización en alta/edición de producto, ver ADR 0005).
