# ADR 0009: Sesión, carrito y cache de lecturas (MySQL-only)

## Estado

Aceptado

## Contexto

`AGENTS.md` §3 lista "carritos y sesiones" dentro de MySQL y §9 prohíbe desperdiciar memoria en
hardware limitado. Se necesitan sesiones (guest/autenticada), persistencia del carrito y una cache
para las lecturas CQRS del catálogo (ADR 0005). La alternativa natural (Redis) añade un servicio y
consume RAM.

## Decisión

Mantener **sesión, carrito y reservas en MySQL** con un pool de conexiones optimizado, y cachear las
lecturas del catálogo **en memoria del proceso** (sin servicio externo). Meilisearch actúa como
índice de lectura principal (ADR 0006).

## Alternativas consideradas

- **MySQL + Redis** — sesiones más rápidas, TTL de reserva y cache de catálogo, pero suma un
  servicio y RAM; descartado por la restricción de recursos de `AGENTS.md` §9.

## Consecuencias

- Un único datastore, menor superficie operativa y de memoria.
- Trade-off: sin cache compartida, el cache de lecturas es por-proceso; la consistencia de sesión
  depende de la latencia de MySQL bajo carga, lo que exige un pool bien dimensionado.
