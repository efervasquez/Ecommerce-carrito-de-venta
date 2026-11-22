# Informe de Entrega DEV — HU-01 Autoregistro y autenticación de clientes

**Fecha:** 2026-11-21
**Rol:** DEV
**Documento base:** `contratos/CONTRATO-HU-01.md` (v1, aprobada 2026-10-16)
**Tipo de tarea:** Feature
**Rama:** `feat/hu-01-autoregistro`

---

## 1. Qué se construyó

Implementación completa del módulo de autenticación (HU-01) en backend y frontend, respetando el
contrato estricto (rutas, payloads, mensajes visibles exactos) y los ADRs aplicables (`ADR-0003`,
`ADR-0004`, `ADR-0007`, `ADR-0010`, `ADR-0015`, `ADR-0017`, `ADR-0018`, `ADR-0019`).

### Backend (`backend/src/modules/auth/` por capas: Router → Service → Repository)

- `models.py`: Entidades `Usuario` (`email` único, `password_hash`, `rol`, `estado`) y `Token`
  (`token_hash` SHA-256, `tipo`, `usuario_id`, `expira_en`, `usado_en`, `creado_en`) según
  ADR-0003 / ADR-0017.
- `schemas.py`: Modelos Pydantic de petición/respuesta tipados (ADR-0004).
- `security.py`: Token opaco UUID v4 (CSPRNG), hash SHA-256, bcrypt para contraseñas, política de
  complejidad (DP-2: ≥8, mayúscula, minúscula, número) y firma/verificación de JWT HS256 con
  claims `sub`, `rol`, `scopes` y `exp` de 3600 s (DP-3).
- `repository.py`: Acceso a datos de `usuarios` y `tokens` (SQLAlchemy async).
- `service.py`: Lógica de negocio con anti-enumeración (HTTP 200 idéntico + padding de timing para
  registro), cooldown de 15 min por email, invalidación de tokens previos y flujo de activación de
  un solo uso.
- `router.py`: Endpoints `POST /api/v1/auth/registro`, `POST /api/v1/auth/activar`,
  `POST /api/v1/auth/login`, `GET /api/v1/auth/me` con dependencias de sesión y bearer JWT.

### Soporte transversal

- `backend/src/core/rate_limit.py`: `RateLimiter` en memoria (ventana fija) + middleware
  `AuthRateLimitMiddleware` que aplica **3 peticiones/minuto por IP** sobre los POST de auth y
  responde HTTP 429 con el mensaje exacto (ADR-0019, segunda línea de defensa).
- `backend/src/core/broker.py`: `publish_event()` que publica JSON persistente en la cola
  `email.auth` (evento `auth.activacion_solicitada`) según ADR-0007/ADR-0018.
- `backend/src/config.py`: variables `JWT_SECRET`, `JWT_EXPIRES_SECONDS` (3600) y
  `FRONTEND_BASE_URL` (base del `url_activacion`).
- `backend/requirements.txt`: dependencias `pyjwt` y `bcrypt`.
- `backend/alembic/versions/0001_create_usuarios_y_tokens.py`: migración que crea las tablas
  `usuarios` y `tokens` con índices (`email` único, `token_hash`, `usuario_id`).

### Frontend (React 18 + Vite + TanStack Query + Zustand + react-router-dom)

- `src/pages/Registro.tsx`: ruta `/registro`, input `email` (id/name), botón `"Registrarme"`, error
  visual de formato sin enviar petición y mensaje de éxito exacto.
- `src/pages/Activar.tsx`: ruta `/activar?token=...`, inputs `password`/`confirm_password`, botón
  `"Activar cuenta"`, mensaje `"Cuenta activada exitosamente"` y enlace a `/login`.
- `src/pages/Login.tsx`: ruta `/login`, inputs `email`/`password`, botón `"Iniciar sesión"`,
  guarda sesión en Zustand y redirige a `/`.
- `src/pages/Home.tsx`: vista principal `/` con sesión persistente y cierre de sesión.
- `src/services/auth.ts`: cliente tipado para los 4 endpoints con `ApiError` (status + detail).
- `src/store/useAuthStore.ts`: store Zustand de sesión (ADR-0010).
- `src/App.tsx`: enrutado con `react-router-dom` (`/`, `/registro`, `/activar`, `/login`).
- `frontend/package.json`: dependencia `react-router-dom`.

---

## 2. Variables de entorno nuevas

| Variable | Default | Uso |
|---|---|---|
| `JWT_SECRET` | `insecure-dev-secret-cambiar-en-produccion` | Firma de JWT (definir secreto fuerte en producción) |
| `JWT_EXPIRES_SECONDS` | `3600` | TTL del access_token (DP-3) |
| `FRONTEND_BASE_URL` | `https://localhost:5173` | Base del `url_activacion` del correo |

Documentadas en `backend/.env.example`.

---

## 3. Cómo se prueba a mano

### Migraciones y arranque del backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\uvicorn src.main:app --port 8000 --reload
```

### Flujo completo por HTTP

1. **Registro** (`POST /api/v1/auth/registro`, body `{"email":"cliente@ejemplo.com"}`):
   responde `200 {"message":"Si el correo ingresado es válido, recibirás un enlace de activación en tu buzón."}`,
   crea `Usuario` en `pendiente_activacion` y publica `auth.activacion_solicitada` en `email.auth`.
2. **Obtener el token crudo** del evento de RabbitMQ (payload `payload.token`); abrir en el frontend
   `http://localhost:5173/activar?token=<token>`.
3. **Activar** (`POST /api/v1/auth/activar`, body `{"token":"<token>","password":"Password123!"}`):
   responde `200 {"message":"Cuenta activada exitosamente. Ya puedes iniciar sesión."}`.
4. **Login** (`POST /api/v1/auth/login`, body `{"email":"...","password":"Password123!"}`): responde
   `200` con `access_token`, `token_type:"bearer"`, `expires_in:3600` y `usuario`.
5. **Sesión** (`GET /api/v1/auth/me` con header `Authorization: Bearer <access_token>`): responde
   `200 {"id":...,"email":...,"rol":"cliente","estado":"activo"}`.

### Casos de error verificados

- Email inválido → `422 {"detail":"Formato de correo electrónico inválido"}`.
- Payload vacío / campo ausente → `422 {"detail":"El campo <campo> es requerido."}`.
- Contraseña débil → `422` con mensaje de complejidad exacto.
- Token usado/expirado/inexistente → `400 {"detail":"El enlace de activación es inválido o ha expirado."}`.
- Login con credenciales inválidas o cuenta no activada → `401 {"detail":"Credenciales inválidas o cuenta no activada."}`.
- Cuenta suspendida → `403 {"detail":"Cuenta suspendida. Por favor, contacte a soporte."}`.
- Token JWT ausente/inválido → `401 {"detail":"No autenticado o token inválido."}`; expirado → `401 {"detail":"Token expirado. Inicie sesión nuevamente."}`.
- 4ª petición POST de auth en <60 s desde la misma IP → `429 {"detail":"Demasiadas solicitudes. Por favor, intente nuevamente en unos minutos."}`.

### Frontend

```powershell
cd frontend
npm install
npm run build        # valida tipos TypeScript
npm run dev          # http://localhost:5173 -> /registro, /activar, /login
```

---

## 4. Notas para el TESTER

- **Rate limit en memoria**: el limitador es un singleton en `src.core.rate_limit.auth_rate_limiter`.
  Como las pruebas con `TestClient` comparten IP (`testclient`), tras 3 POST de auth se obtendrá 429.
  Para aislar cada prueba: llamar `auth_rate_limiter.reset()` entre casos, o enviar
  `X-Forwarded-For` con un valor distinto por petición (el limitador prefiere esa cabecera).
- **RabbitMQ puede no estar activo**: la publicación del evento en `email.auth` es *best-effort*
  (se registra `WARNING` si falla) y no bloquea el `200` del registro; la cuenta y el token sí se
  crean. Para observar el evento, tener el broker arriba.
- **bcrypt**: el hash de contraseña se compara con `bcrypt.checkpw`; el login con email inexistente
  ejecuta una verificación ficticia para igualar timing (anti-enumeración).

## 5. Rutas tocadas y cumplimiento de reglas

- **Tocadas (solo DEV):** `backend/src/**`, `backend/alembic/**`, `backend/requirements.txt`,
  `backend/.env.example`, `frontend/src/**`, `frontend/package.json`, `frontend/package-lock.json`.
- **No tocadas:** `backend/tests/**` y `frontend/tests/**` (rutas del TESTER).
- No se agregaron dependencias no decididas salvo `pyjwt`/`bcrypt` (exigidas por ADR-0004/0017) y
  `react-router-dom` (exigida por las rutas observables del contrato §2/§3.5).
