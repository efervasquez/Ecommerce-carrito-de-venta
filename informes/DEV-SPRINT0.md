# Informe de Entrega DEV — Sprint 0 (Walking Skeleton)

**Fecha:** 2026-10-16  
**Rol:** DEV  
**Documento base:** `SPRINT0.md` (Versión Aprobada)  
**Rama:** `carrito-Edgar`  

---

## 1. Qué se construyó

Se completó la implementación integral del esqueleto técnico funcional (Sprint 0) de la plataforma e-commerce de **Botica la Luz**, respetando estrictamente los ADRs transversales aplicables (`ADR-0001`, `ADR-0002`, `ADR-0010`, `ADR-0014`), las resoluciones mixtas acordadas y el mapa de propiedad de rutas (`AGENTS.md`).

### Backend (Python 3.12+ / FastAPI / SQLAlchemy / aio-pika / Alembic)
- `backend/requirements.txt` y `backend/requirements-dev.txt`: Especificación de dependencias base de producción (FastAPI, uvicorn, pydantic, pydantic-settings, sqlalchemy con asyncio y greenlet, aiomysql, aio-pika, alembic) y herramientas de desarrollo (pytest, pytest-asyncio, httpx).
- `backend/.env.example`: Plantilla exhaustiva de variables de entorno para MySQL local (servicio `MySQL92` en `127.0.0.1`), RabbitMQ, logs estructurados y CORS.
- `backend/src/config.py`: Centralización tipada de configuración mediante `pydantic-settings` (`Settings`, `SettingsConfigDict`), con parser resiliente de orígenes CORS y cálculo dinámico de `database_url`.
- `backend/src/core/logging.py`: Formateador JSON estructurado (`JSONFormatter`) según `ADR-0015`, filtro de inyección de contexto y middleware asíncrono `CorrelationIdMiddleware` para captura/generación y propagación del header `X-Correlation-ID`.
- `backend/src/core/database.py`: Motor asíncrono SQLAlchemy (`create_async_engine`) conectado a MySQL vía `aiomysql`, con pool parametrizado (`pool_size=10`, `max_overflow=5`, `pool_pre_ping=True`, `pool_recycle=3600`) y generador de sesiones `get_db_session()`.
- `backend/src/core/broker.py`: Conexión asíncrona robusta a RabbitMQ (`aio-pika.connect_robust`), función de cierre ordenado y método de comprobación de salud `ping_broker()`.
- `backend/src/modules/health/`: Estructura limpia por capas (`Handler/Route -> Service -> Repository`) para el health check:
  - `schemas.py`: Modelo Pydantic `HealthResponse` (`status`, `mysql`, `rabbitmq`).
  - `repository.py`: Sondeo físico de conectividad ejecutando `SELECT 1` en MySQL y apertura de canal en RabbitMQ.
  - `service.py`: Evaluación concurrente con `asyncio.gather`, orquestando códigos HTTP 200 (ok) y 503 (unhealthy ante fallo).
  - `router.py`: Exposición del endpoint `GET /api/v1/health` (y `/api/v1/health/`) documentado en OpenAPI.
- `backend/src/main.py`: Factoría `create_app()` con FastAPI, gestión de ciclo de vida `lifespan` para cierre de conexiones, middlewares de Correlation ID y CORS restrictivo, y registro de router health.
- `backend/src/workers/main.py`: Entrypoint independiente (`python -m src.workers.main`) desacoplado de IIS (ADR-0001, ADR-0007), con conexión a RabbitMQ, log JSON de liveness y soporte para flags `--once` y apagado limpio ante señales.
- `backend/alembic.ini` y `backend/alembic/`: Inicialización base de migraciones con soporte asíncrono en `env.py`, apuntando a `Base.metadata` con cero tablas de negocio en Sprint 0.
- `backend/web.config`: Configuración perimetral para IIS 10 con `HttpPlatformHandler`, límites de payload en `requestFiltering` (10 MB máx., 4096 bytes query string) y cabeceras de seguridad (`Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Content-Security-Policy` autorizando Stripe).

### Frontend (React 18 / Vite / TypeScript / TanStack Query / Zustand)
- `frontend/package.json`: Dependencias base instaladas (React 18, `@tanstack/react-query`, `zustand`, TypeScript, Vite, Vitest).
- `frontend/vite.config.ts` y `frontend/tsconfig.json`: Configuración de compilación con soporte de types de Vite, configuración de proxy para `/api` hacia `http://127.0.0.1:8000` y configuración para Vitest.
- `frontend/src/services/api.ts`: Cliente tipado `fetchHealthStatus()` para consumo reactivo de `GET /api/v1/health`.
- `frontend/src/store/useAppStore.ts`: Store Zustand inicial para gestión de estado de cliente/UI según ADR-0010.
- `frontend/src/components/HealthStatus.tsx`: Componente visual reactivo con TanStack Query (`useQuery`) que visualiza el estado global, el estado de MySQL y RabbitMQ, y botón de refresco manual.
- `frontend/src/App.tsx` y `frontend/src/main.tsx`: Envoltorio de la aplicación con `QueryClientProvider` y montaje en DOM.
- `frontend/index.html` y `frontend/public/favicon.svg`: Estructura HTML base y assets públicos.

### Infraestructura
- `infra/setup-worker-service.ps1`: Script de automatización en PowerShell para instalar y configurar el worker como Servicio de Windows supervisado 24/7 mediante **NSSM** (`BoticaLaLuzWorker`).

---

## 2. Variables de entorno necesarias

Definidas en `backend/.env.example` y consumidas por `src.config.Settings`:
- `APP_ENV`: Entorno de ejecución (`development` / `production`).
- `APP_PORT`: Puerto HTTP de la aplicación (default: `8000`).
- `LOG_LEVEL`: Nivel de logging (`INFO`, `DEBUG`, `WARN`, `ERROR`).
- `CORS_ORIGINS`: Lista JSON de orígenes autorizados (ej: `["http://localhost:5173","http://127.0.0.1:5173"]`).
- `MYSQL_HOST`: Dirección IP de la instancia local de MySQL (default: `127.0.0.1`).
- `MYSQL_PORT`: Puerto de escucha de MySQL (default: `3306`).
- `MYSQL_USER`: Usuario de base de datos (default: `ecommerce_user`).
- `MYSQL_PASSWORD`: Contraseña de base de datos.
- `MYSQL_DB`: Nombre de la base de datos (default: `ecommerce_botica`).
- `MYSQL_POOL_SIZE`: Tamaño base del pool de conexiones (default: `10`).
- `MYSQL_MAX_OVERFLOW`: Desbordamiento máximo permitido en el pool (default: `5`).
- `RABBITMQ_URL`: URL de conexión al broker local (default: `amqp://guest:guest@localhost:5672/`).

---

## 3. Cómo se prueba y arranca a mano

### Backend
1. **Activar el entorno virtual**:
   ```powershell
   .\backend\.venv\Scripts\Activate.ps1
   ```
2. **Arrancar el servidor HTTP**:
   ```powershell
   cd backend
   .\.venv\Scripts\uvicorn src.main:app --port 8000 --reload
   ```
3. **Comprobar OpenAPI y Health Check**:
   - Abrir en navegador: `http://localhost:8000/docs` (Swagger UI operativo).
   - Consultar: `http://localhost:8000/api/v1/health`
     - Con servicios activos: HTTP 200 `{"status":"ok","mysql":"connected","rabbitmq":"connected"}`
     - Con dependencias offline: HTTP 503 `{"status":"unhealthy","mysql":"disconnected","rabbitmq":"disconnected"}` con cabecera `X-Correlation-ID`.
4. **Comprobar el worker de fondo**:
   - Modo liveness puntual:
     ```powershell
     cd backend
     .\.venv\Scripts\python -m src.workers.main --once
     ```
   - Modo continuo supervisado:
     ```powershell
     cd backend
     .\.venv\Scripts\python -m src.workers.main
     ```

### Frontend
1. **Instalar dependencias**:
   ```powershell
   npm --prefix frontend install
   ```
2. **Compilar y validar tipos TypeScript**:
   ```powershell
   npm --prefix frontend run build
   ```
3. **Iniciar servidor de desarrollo**:
   ```powershell
   npm --prefix frontend run dev
   ```
   Acceder a `http://localhost:5173` para visualizar el componente `HealthStatus`.

---

## 4. Estado de rutas y cumplimiento de reglas

- **Rutas tocadas:** Únicamente rutas asignadas al rol `DEV` en `AGENTS.md` y `informes/DEV-SPRINT0.md`.
- **Rutas no tocadas:** Cero modificaciones en rutas del `TESTER` (`backend/tests/**`, `frontend/tests/**`) ni en documentación reservada a `LEAD/humano`.
- **Cero lógica de negocio:** No se crearon modelos, tablas, rutas ni componentes para usuarios, catálogo, carrito, pedidos, pagos, OCR ni despacho. Todo el alcance corresponde estrictamente al esqueleto técnico del Sprint 0.
