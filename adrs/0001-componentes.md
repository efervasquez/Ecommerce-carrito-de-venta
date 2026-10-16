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
asíncronos (consumidores de eventos RabbitMQ) compartiendo el mismo código base.

Para evitar que el **Idle Timeout de IIS** suspenda los workers en periodos de inactividad o que
múltiples procesos de IIS dupliquen consumidores (C-03), **se desacopla la ejecución operativa**:
1. **API Web (IIS 10):** Corre `uvicorn src.main:app` bajo `HttpPlatformHandler` atendiendo exclusivamente tráfico HTTP `/api/v1`.
2. **Workers de Fondo (Servicio de Windows):** Se ejecutan de forma continua 24/7 como un servicio del sistema operativo supervisado vía **NSSM** (`python -m src.workers.main`).

## Alternativas consideradas

- **Microservicios reales** — desacoplamiento y escala independiente, pero multiplica deploys,
  procesos y superficie operativa; sobredimensionado para el MVP y el equipo.
- **Monolito sin bus de eventos** — aún más simple, pero incumple el patrón obligatorio de
  `AGENTS.md` ("todo flujo desacoplado debe ir por el broker de eventos local") y acopla los flujos
  de despacho/OCR/notificación a la petición HTTP.
- **Workers integrados dentro del proceso FastAPI en IIS** — descartado por C-03: IIS suspende
  procesos inactivos tras 20 minutos (matando los consumidores de RabbitMQ) y duplica workers si el
  App Pool levanta múltiples procesos (`maxProcesses > 1`).

## Consecuencias

- Un solo código base a mantener, cumpliendo SOLID/CQRS/RBAC por módulos y capas.
- Desacoplamiento operativo total: la API HTTP puede reiniciarse o reciclarse en IIS sin interrumpir
  el consumo de colas de RabbitMQ, y los workers operan 24/7 sin riesgo de suspensión.
- Trade-off: se configura un servicio supervisado en Windows (NSSM) para el entrypoint de los workers.
