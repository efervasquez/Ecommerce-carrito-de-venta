# ADR 0010: Estado del frontend (TanStack Query + Zustand)

## Estado

Aceptado

## Ámbito

Transversal — gestión de estado del frontend para toda la aplicación.

## Contexto

El frontend React debe manejar dos tipos de estado: el estado de servidor (catálogo con scroll
infinito, carrito, pedidos) que debe cachearse y refetcharse, y el estado de cliente (sesión, UI).
El scroll infinito sin paginación (RF-02.1) exige fetching paginado por cursor/incremental.

## Decisión

Usar **TanStack Query** para el estado de servidor (caching, refetch, paginación por cursor para
scroll infinito) y **Zustand** para el estado de cliente (sesión activa, UI).

## Alternativas consideradas

- **React Context + Hooks nativos (`useReducer`)** — cero dependencias añadidas y bundle mínimo, pero
  obliga a construir manualmente caching de peticiones, reintentos en red, deduplicación y gestión
  de cursores para el scroll infinito, incrementando el esfuerzo de desarrollo.
- **SWR + Zustand** — SWR es una alternativa ligera y madura, pero TanStack Query ofrece soporte
  superior de primer nivel para paginación incremental (`useInfiniteQuery`), esencial para la lista
  continua del catálogo de la botica (RF-02.1).
- **Zustand puro para servidor y cliente** — unifica toda la gestión en una sola librería, pero
  obliga a implementar a mano la lógica de invalidación y caching de red de TanStack Query.
- **Redux Toolkit + RTK Query** — robusto para estado global complejo empresarial, pero con
  boilerplate excesivo y curva de aprendizaje alta para la escala y equipo del MVP.

## Consecuencias

- Código de fetching/refetch reducido y rendimiento predecible en listas largas.
- **Virtualización de DOM (S-01):** Para evitar saturar la memoria en dispositivos móviles al hacer
  scroll sobre cientos de productos farmacéuticos, se acopla `@tanstack/react-virtual` al renderizado
  de la lista infinita.
- Trade-off: dos librerías de estado que conviven; hay que fijar una regla clara de qué va a cada
  una para no duplicar estado (servidor a TanStack Query, UI/sesión a Zustand).
