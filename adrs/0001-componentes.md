# ADR 0001: Arquitectura de componentes (monolito modular + workers)

## Estado

Aceptado

## Contexto

El `AGENTS.md` manda una arquitectura orientada a eventos (EDA) con "microservicios locales"
comunicados por un bus de eventos central. Sin embargo, el PRD define un MVP para una botica
pequeña (Botica la Luz), con un equipo de desarrollo muy reducido y despliegue on-premise sobre un
único servidor Windows/IIS. Microservicios reales (un proceso y deploy por dominio) suponen una
carga operativa y de infraestructura desproporcionada para el volumen objetivo (250 usuarios
concurrentes) y para el hardware limitado que `AGENTS.md` §9 obliga a respetar.

## Decisión

Construir un **monolito modular**: un único backend FastAPI organizado por capas
(`Handler/Route -> Controller -> Service -> Repository`) con módulos por dominio (auth, catálogo,
carrito, pedidos, OCR, despacho, reclamos, stock), un único frontend React/Vite, y workers
asíncronos (consumidores de eventos) en el mismo código. Los flujos asíncronos se desacoplan por el
bus de eventos (ver ADR 0007), pero no hay servicios desplegados por separado.

## Alternativas consideradas

- **Microservicios reales** — desacoplamiento y escala independiente, pero multiplica deploys,
  procesos y superficie operativa; sobredimensionado para el MVP y el equipo.
- **Monolito sin bus de eventos** — aún más simple, pero incumple el patrón obligatorio de
  `AGENTS.md` ("todo flujo desacoplado debe ir por el broker de eventos local") y acopla los flujos
  de despacho/OCR/notificación a la petición HTTP.

## Consecuencias

- Un solo artefacto a empaquetar y desplegar en IIS; se cumple SOLID/CQRS/RBAC por módulos y capas.
- Trade-off: el escalado es vertical (todo el monolito), no por dominio; si un flujo degrada la CPU
  (p. ej. OCR), afecta al proceso completo, por lo que OCR y trabajos pesados deben ir a workers.
