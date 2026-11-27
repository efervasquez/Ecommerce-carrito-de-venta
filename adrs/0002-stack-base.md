# ADR 0002: Stack tecnológico base (FastAPI + React/Vite + MySQL + IIS on-premise)

## Estado

Aceptado

## Ámbito

Transversal — aplica a todo el sistema (stack tecnológico base).

## Contexto

El proyecto nace greenfield, pero el `AGENTS.md` del repositorio fija una pila específica para el
entorno on-premise. El usuario confirmó explícitamente que **manda `AGENTS.md`**, interpretando
"infraestructura gratuita" como *sin costo de licencias* (servidor propio) y no como free tiers de
cloud. Esto descarta migrar a Vercel/Render/Supabase y ata el stack a Windows 11 Pro + IIS 10.

## Decisión

- Backend: **Python 3.12 + FastAPI** (async/await), servido en **IIS 10** vía `HttpPlatformHandler`
  o FastCGI.
- Frontend: **React 18 + Vite** (Web App responsive, no app nativa).
- Base de datos: **MySQL Server** (instancia local, escuchando solo en `127.0.0.1`).
- Gestión de dependencias: **poetry** (Python) / **pnpm** (JS).
- Testing: **pytest** / **Jest + React Testing Library + Cypress**.

## Alternativas consideradas

- **Cloud free tier (Vercel/Neon/PlanetScale)** — despliegue simple y sin servidor propio, pero el
  usuario descartó la nube y `AGENTS.md` exige aislamiento de red on-premise con MySQL local.
- **Node.js/NestJS en backend** — unificar lenguaje con el frontend, pero `AGENTS.md` manda Python
  y FastAPI; cambiarlo añadiría riesgo sin beneficio para el equipo.

## Consecuencias

- Cero costos de licencias (todo open source) y control total del dato (LPDP, red local).
- Trade-off: se asume la complejidad operativa de IIS/FastCGI/HttpPlatformHandler y del
  mantenimiento on-premise (respaldos, firewall, pool de aplicaciones) sobre un solo servidor.
