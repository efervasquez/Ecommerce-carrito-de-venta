# ADR 0010: Estado del frontend (TanStack Query + Zustand)

## Estado

Aceptado

## Contexto

El frontend React debe manejar dos tipos de estado: el estado de servidor (catálogo con scroll
infinito, carrito, pedidos) que debe cachearse y refetcharse, y el estado de cliente (sesión, UI).
El scroll infinito sin paginación (RF-02.1) exige fetching paginado por cursor/incremental.

## Decisión

Usar **TanStack Query** para el estado de servidor (caching, refetch, paginación por cursor para
scroll infinito) y **Zustand** para el estado de cliente (sesión activa, UI).

## Alternativas consideradas

- **Redux Toolkit + RTK Query** — robusto para estado global complejo, pero más boilerplate y curva
  para un MVP.

## Consecuencias

- Código de fetching/refetch reducido y rendimiento predecible en listas largas.
- Trade-off: dos librerías de estado que conviven; hay que fijar una regla clara de qué va a cada
  una para no duplicar estado.
