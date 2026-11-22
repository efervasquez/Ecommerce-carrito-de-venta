# ADR 0006: Motor de búsqueda difusa (Meilisearch)

## Estado

Aceptado

## Ámbito

Historia de usuario — HU-03 (Búsqueda difusa y catálogo scroll infinito).

## Contexto

El PRD RF-02.1 exige *Fuzzy Search* tolerante a errores de tipeo (ej. mapear "camiaa" → "camisa") y
renderizado en scroll infinito sin paginación. La búsqueda debe responder en <2.5 s bajo 250
usuarios concurrentes (RNF-01). La base es MySQL, cuyo `FULLTEXT` nativo no ofrece tolerancia real
a typos.

## Decisión

Usar **Meilisearch self-hosted** como motor de búsqueda e índice de lectura del catálogo, con
typo-tolerance configurable, ranking por relevancia y soporte de filtros (categoría, oferta,
precios bajos, requiere receta).

### Mecanismo de sincronización MySQL → Meilisearch (S-01)

1. **Sincronización en tiempo casi real vía eventos:** Al persistir o mutar un producto en MySQL
   (alta, modificación o contingencia de stock manual RF-05), el servicio emite un evento
   `catalogo.producto_modificado` al bus RabbitMQ. Un worker asíncrono consume el evento y ejecuta
   un `upsert` puntual en el índice de Meilisearch.
2. **Idempotencia y reintentos:** Si Meilisearch estuviera temporalmente inaccesible, el worker
   aplica la política de reintentos con backoff (ADR 0007).
3. **Reconciliación y reindexación periódica:** Se dispone de un comando CLI programado vía Tarea de
   Windows que efectúa una reindexación completa de consistencia fuera de horas pico (semanal).

## Alternativas consideradas

- **MySQL FULLTEXT + n-gram** — sin servicios extra, pero la tolerancia a errores de tipeo es pobre
  y el ranking limitado; no cumple bien RF-02.1.
- **Elasticsearch** — potente y maduro, pero pesado en RAM; sobredimensionado y en contra de
  `AGENTS.md` §9 (optimización de memoria en hardware limitado).

## Consecuencias

- Búsqueda difusa de calidad con poco esfuerzo de integración y bajo consumo relativo de recursos.
- Sincronización robusta desacoplada por eventos sin frenar las transacciones de escritura en MySQL.
- Trade-off: un servicio local adicional a mantener, y eventual consistencia de milisegundos entre
  MySQL y el índice.
