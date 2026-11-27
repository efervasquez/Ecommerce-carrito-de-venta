# SPRINT 0 — Plataforma E-commerce Botica la Luz

**Estado:** Aprobado (2026-10-16, usuario humano)  
**Fuentes:** `TECH-DESIGN.md`, `adrs/`, `AGENTS.md`

---

## 1. ADRs que aplican (transversales)

| ADR | Decisión | Por qué aplica ahora |
|---|---|---|
| [ADR-0001](adrs/0001-componentes.md) | Monolito modular FastAPI por capas + workers en proceso dedicado supervisado (NSSM) | Fija la arquitectura de carpetas (`src/`, capas Route -> Controller -> Service -> Repository), la separación operativa entre API HTTP y workers, y los entrypoints base. |
| [ADR-0002](adrs/0002-stack-base.md) | Stack base Python 3.12 + FastAPI, React 18 + Vite, MySQL 127.0.0.1, IIS on-premise | Define las tecnologías, herramientas de desarrollo, empaquetado y runners de prueba para el esqueleto funcional. |
| [ADR-0010](adrs/0010-estado-frontend.md) | TanStack Query (servidor) + Zustand (cliente/UI) en React 18 + Vite | Fija el manejo de estado en frontend. Se inicializa el `QueryClientProvider` y el consumo reactivo del health check en el esqueleto. |
| [ADR-0014](adrs/0014-disponibilidad.md) | Operación single-node on-premise con observabilidad y health check | El esqueleto se despliega en un solo nodo local e instrumenta endpoints de salud y liveness para monitoreo operativo. |

---

## 2. ADRs que NO aplican todavía (de historia)

| ADR | Decisión | Aplica cuando llegue |
|---|---|---|
| [ADR-0005](adrs/0005-cqrs-catalogo.md) | CQRS para lecturas del catálogo con Meilisearch y escrituras en MySQL | HU-03 (Búsqueda difusa y catálogo scroll infinito) y HU-10 (Módulo contingencia de stock) |
| [ADR-0006](adrs/0006-busqueda-fuzzy.md) | Búsqueda difusa con Meilisearch self-hosted y sincronización por eventos | HU-03 (Búsqueda difusa y catálogo scroll infinito) |
| [ADR-0008](adrs/0008-ocr.md) | OCR con Tesseract en worker (ThreadPoolExecutor máx. 2 hilos) y fallback manual | HU-06 (Automatización OCR recetas médicas) |
| [ADR-0011](adrs/0011-reserva-stock.md) | Reserva de stock al agregar con TTL, prórroga en checkout y purga programada | HU-05 (Carrito de compras y persistencia) y HU-07 (Pasarela de pagos Stripe) |
| [ADR-0012](adrs/0012-erp.md) | Integración ERP post-MVP mediante `InventoryProviderProtocol` | HU-05, HU-07 y HU-10 (Gestión de stock e inventario) |
| [ADR-0013](adrs/0013-consistencia-pago.md) | Checkout en dos fases con prórroga de reserva y confirmación atómica en webhook | HU-07 (Pasarela de pagos Stripe sandbox) |
| [ADR-0016](adrs/0016-anti-abuso-carrito-guest.md) | Límites SKU (máx 3), 10 productos y rate limiting por IP en carrito guest | HU-05 (Carrito de compras y persistencia) |
| [ADR-0017](adrs/0017-tokens-seguridad.md) | Tokens opacos SHA-256 de un solo uso con cooldown anti-spam para activación/recuperación | HU-01 (Autoregistro) y HU-02 (Recuperación de contraseña) |
| [ADR-0018](adrs/0018-transporte-smtp.md) | Transporte de correo transaccional vía relay externo (Brevo 300 mails/día) | HU-01, HU-02 y HU-08 (Despacho logístico) |

---

## 3. Acuerdos y Resoluciones de ADRs Mixtos

| ADR | Alcance para Sprint 0 | Alcance diferido a HUs | Resolución acordada |
|---|---|---|---|
| [ADR-0003](adrs/0003-modelo-datos.md) | Infraestructura de persistencia: Alembic + SQLAlchemy async con MySQL local (`MySQL92`). | Tablas de dominio (`Usuario`, `Producto`, `Carrito`, `Pedido`, etc.). | Alembic configurado y verificado con tabla base `alembic_version`. Cero tablas de negocio en Sprint 0. |
| [ADR-0004](adrs/0004-contratos-api.md) | Convención REST JSON `/api/v1`, OpenAPI autogenerado, Pydantic y endpoint transversal `GET /api/v1/health`. | Middlewares de autenticación JWT/RBAC, cookies de sesión guest y contratos de jobs OCR. | `GET /api/v1/health` sondea MySQL y RabbitMQ reportando `{"status":"ok","mysql":"connected","rabbitmq":"connected"}` (HTTP 200) o HTTP 503 ante caída. |
| [ADR-0007](adrs/0007-broker-workers.md) | Conexión async a RabbitMQ (`aio-pika`), entrypoint del worker (`src.workers.main`) con liveness y verificación en health check. | Declaración de colas de negocio (`ocr.procesar`, `email.*`, etc.), DLQs y lógica de consumidores. | Parámetros configurables vía `.env` (`localhost:5672`). Pruebas de integración en pytest cubren tanto conexión exitosa como simulación de fallo (503). |
| [ADR-0009](adrs/0009-sesion-cache.md) | Pool de conexiones optimizado de MySQL (SQLAlchemy async / aiomysql) configurado en FastAPI. | Cache LRU de catálogo en memoria y tablas de persistencia de sesión/carrito en MySQL. | Pool configurado con defaults parametrizados (`pool_size=10`, `max_overflow=5`). |
| [ADR-0015](adrs/0015-lpdp.md) | Logger estructurado en JSON con inyección de `correlation_id` (sin loguear secretos) y variables de entorno seguras (`.env`). | Cifrado TDE InnoDB en tablas de negocio y política de retención de recetas. | Middleware de `correlation_id` y formateador JSON incorporados transversalmente desde Sprint 0. |
| [ADR-0019](adrs/0019-seguridad-perimetral-iis.md) | CORS restrictivo hacia el frontend y cabeceras de seguridad base en middleware FastAPI y plantilla `backend/web.config`. | Reglas de rate limiting por endpoint en IIS, CSP autorizada de Stripe y exclusiones de URL Rewrite para catálogo. | DEV crea `backend/web.config` con HttpPlatformHandler y security headers perimetrales estándar. |

---

## 4. Propiedad de rutas

| Rol | Rutas |
|---|---|
| **TESTER** | `backend/tests/**`, `frontend/tests/**`, `frontend/src/**/*.test.tsx`, `frontend/src/**/*.spec.ts` |
| **DEV** | `backend/src/**`, `backend/alembic/**`, `backend/alembic.ini`, `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/web.config`, `backend/.env.example`, `frontend/src/**` (excluyendo tests), `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/vite.config.*`, `frontend/tsconfig.*`, `frontend/index.html`, `frontend/public/**`, `infra/**` |
| **Solo LEAD / humano** | `AGENTS.md`, `CLAUDE.md`, `.agents/**`, `.claude/**`, `SPRINT0.md`, `contratos/**`, `docs/**`, `HUs/**`, `adrs/**`, `TECH-DESIGN.md` |

> Esta tabla también se encuentra copiada en `AGENTS.md` → `## Propiedad de rutas`.

---

## 5. Definition of Done — esqueleto

| # | Criterio | Cómo se verifica |
|---|---|---|
| 1 | El backend arranca en local y expone OpenAPI | Comando: `uvicorn src.main:app --port 8000` (desde entorno `venv`). Acceso a `http://localhost:8000/docs` devuelve HTTP 200 con Swagger UI. |
| 2 | El backend se conecta a dependencias principales (MySQL y RabbitMQ) | Prueba automatizada: prueba de integración en `backend/tests/test_health.py` que comprueba ping exitoso a MySQL y RabbitMQ. |
| 3 | Responde en el endpoint exacto `GET /api/v1/health` | Prueba automatizada: `GET http://localhost:8000/api/v1/health` responde HTTP 200 con payload `{"status":"ok","mysql":"connected","rabbitmq":"connected"}` cuando los servicios están activos, y HTTP 503 si alguno falla. |
| 4 | El frontend arranca en local con React 18 + Vite | Comando: `npm --prefix frontend run dev` o `pnpm --prefix frontend dev`. Levanta en `http://localhost:5173` sin errores de compilación. |
| 5 | El frontend consume y visualiza el estado del health check | Prueba unitaria/componente: El frontend renderiza un indicador de estado consumiendo `GET /api/v1/health` vía TanStack Query (`@tanstack/react-query`). |
| 6 | El proceso worker de segundo plano arranca | Comando: `python -m src.workers.main`. Se conecta al broker RabbitMQ y emite un log JSON de liveness sin excepciones. |
| 7 | Trazabilidad con Logging JSON y Correlation ID | Prueba automatizada: Cada solicitud HTTP genera logs estructurados en JSON que incluyen el campo `correlation_id` (propagado o generado en cabecera `X-Correlation-ID`). |
| 8 | Configuración centralizada por variables de entorno | Prueba automatizada: Carga de settings vía `pydantic-settings` desde `.env` sin credenciales hardcodeadas en código fuente. |
| 9 | Los runners de pruebas se ejecutan correctamente | Comandos: `pytest` (backend) y `npm test` / `pnpm test` con `Vitest` (frontend) se ejecutan y finalizan en verde (exit code 0). |
| 10 | Respeta la arquitectura monolítica modular por capas | Inspección de código: Módulo health estructurado en `Handler/Route -> Service -> Repository` dentro de `backend/src/`. |
| 11 | Cero lógica de negocio | Revisión humana: Ningún modelo, migración ni endpoint de usuarios, productos, carritos, recetas, pedidos, pagos ni despacho está implementado. |

---

## 6. Plan

### DEV crea
- `backend/requirements.txt` y `backend/requirements-dev.txt` con: FastAPI, uvicorn, pydantic, pydantic-settings, sqlalchemy, aiomysql, aio-pika, alembic, httpx, pytest, pytest-asyncio.
- `backend/alembic.ini` y carpeta `backend/alembic/` (setup inicial de migraciones sin tablas de negocio).
- `backend/.env.example` con plantilla de variables (MySQL host/user/pass/db, RabbitMQ url, log level, cors origins).
- `backend/src/config.py` con modelo de configuración Pydantic Settings.
- `backend/src/core/logging.py` con formateador JSON estructurado y middleware de `correlation_id`.
- `backend/src/core/database.py` con motor asíncrono SQLAlchemy y sessionmaker para MySQL.
- `backend/src/core/broker.py` con cliente de conexión asíncrona a RabbitMQ (`aio-pika`).
- `backend/src/modules/health/` (router `GET /api/v1/health`, servicio y repository de verificación de MySQL y RabbitMQ).
- `backend/src/main.py` (aplicación FastAPI, middlewares de CORS y Correlation ID, registro de router `/api/v1/health`).
- `backend/src/workers/main.py` (entrypoint del proceso worker con conexión a RabbitMQ y log de liveness).
- `backend/web.config` (plantilla de configuración para IIS con HttpPlatformHandler y security headers).
- `frontend/package.json` con dependencias: React 18, Vite, `@tanstack/react-query`, `zustand`, TypeScript, `vitest`, `@testing-library/react`, `jsdom`.
- `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`.
- `frontend/src/main.tsx` y `frontend/src/App.tsx` configurando `QueryClientProvider`.
- `frontend/src/services/api.ts` (cliente de conexión para `GET /api/v1/health`).
- `frontend/src/components/HealthStatus.tsx` (componente visual de estado de conectividad del sistema).

### TESTER crea
- `backend/tests/conftest.py` (fixtures de testing para FastAPI TestClient / httpx AsyncClient con soporte para testear estados de dependencias).
- `backend/tests/test_health.py` (pruebas de `GET /api/v1/health`: caso 200 con MySQL y RabbitMQ activos, caso 503 ante fallas simuladas de conexión).
- `backend/tests/test_config.py` (pruebas de validación de carga de configuración desde variables de entorno).
- `backend/tests/test_logging.py` (pruebas de propagación del header `X-Correlation-ID` y estructura JSON en logs).
- `frontend/tests/HealthStatus.test.tsx` (prueba unitaria del componente de estado de salud con TanStack Query y Vitest).
- Configuración de runners (`pytest.ini` en backend, scripts `test` con `vitest` en frontend).

### NO se crea
- Tablas ni modelos de base de datos de negocio (`usuarios`, `productos`, `carritos`, `recetas`, `pedidos`, etc.).
- Endpoints de autenticación, catálogo, carrito, OCR, checkout o despacho.
- Consumidores ni colas de mensajería de negocio (`ocr.procesar`, `email.*`, etc.).
- Componentes de UI de catálogo, productos, carrito o flujos de usuario.

---

## 7. Preguntas Abiertas y Resoluciones

1. **Gestor de dependencias de Python:** Resuelto: Usar entorno virtual nativo (`venv`) con `pip` y `requirements.txt` / `requirements-dev.txt`.
2. **Entorno local de RabbitMQ y MySQL:** Resuelto: Usar el servicio de Windows existente `MySQL92` para la base de datos. Para RabbitMQ, conexión real parametrizada en `.env` (`localhost:5672`) y pruebas en `pytest` que verifican tanto el caso conectado como el fallo 503.
3. **Runner de pruebas en frontend:** Resuelto: Usar `Vitest` + `@testing-library/react` integrado con Vite.
4. **Plantilla `web.config` de IIS:** Resuelto: DEV crea `backend/web.config` con `HttpPlatformHandler` y security headers perimetrales base desde el Sprint 0.

---

## 8. Cambios durante el ciclo

| Fecha | Cambio | Aprobado por |
|---|---|---|
| 2026-10-16 | Aprobación del plan y resolución de las 4 preguntas abiertas (Opción A en todas). | Usuario humano |
