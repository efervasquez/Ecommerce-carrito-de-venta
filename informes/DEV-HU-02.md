# Informe de Entrega DEV — HU-02 Recuperación de contraseña

**Fecha:** 2026-11-23  
**Rol:** DEV  
**Documento base:** `contratos/CONTRATO-HU-02.md` (v1, aprobada 2026-11-23)  
**Tipo de tarea:** Feature  
**Rama:** `feat/hu-02-recuperacion`

## 1. Qué se construyó

### Backend

- `POST /api/v1/auth/recuperar`: valida email, responde siempre con
  `Si el email existe, recibirás un correo`, aplica anti-enumeración, cooldown de 15 minutos,
  máximo 3 solicitudes por 24 horas y solo emite recuperación para cuentas activas.
- `POST /api/v1/auth/restablecer`: valida token `recuperacion`, expiración de 1 hora, un solo uso,
  contraseña fuerte, actualización de hash e invalidación de tokens previos.
- Reutilización de `Usuario` y `Token` existentes; no se requiere migración adicional.
- Eventos `auth.recuperacion_solicitada` publicados en la cola durable `email.auth`, con
  `correlation_id`, `timestamp`, `email`, token crudo solo en el evento, `url_recuperacion` y
  `expira_en`.
- El rate limit existente de 3 POST/min/IP se amplió a `recuperar` y `restablecer`.

### Frontend

- Enlace exacto `¿Olvidaste tu contraseña?` en `/login`.
- Nueva pantalla `/recuperar` con campo `email`, botón `Enviar enlace` y mensaje genérico.
- Nueva pantalla `/restablecer?token=<token>` con campos `password`, `confirm_password` y botón
  `Actualizar contraseña`.
- Token inválido/expirado bloquea el formulario y muestra `Solicitar nuevo enlace` hacia `/recuperar`.
- Restablecimiento exitoso muestra confirmación y enlace a `/login`.

## 2. Verificación manual

Backend:

```powershell
cd backend
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\uvicorn src.main:app --port 8000 --reload
```

Casos verificados mediante ASGI HTTP contra MySQL local:

- Recuperación con cooldown: HTTP 200 y mensaje genérico.
- Email inexistente: HTTP 200 y mismo mensaje genérico.
- Email inválido: HTTP 422 con `Formato de correo electrónico inválido`.
- Contraseña débil: HTTP 422 con el mensaje de complejidad exacto; token intacto.
- Restablecimiento válido: HTTP 200, hash actualizado y token consumido.
- Reutilización del token: HTTP 400 con `El enlace de recuperación es inválido o ha expirado.`.
- Login posterior con la nueva contraseña: HTTP 200 bearer.

Frontend:

```powershell
cd frontend
npm run build
```

Resultado: TypeScript y Vite compilan correctamente. El directorio `frontend/dist` fue eliminado
después de la verificación y no se agregó ningún archivo raíz `package.json`/`package-lock.json`.

## 3. Rutas tocadas

- `backend/src/core/rate_limit.py`
- `backend/src/modules/auth/{schemas,repository,router,service}.py`
- `frontend/src/App.tsx`
- `frontend/src/pages/Login.tsx`
- `frontend/src/pages/Recuperar.tsx`
- `frontend/src/pages/Restablecer.tsx`
- `frontend/src/services/auth.ts`
- `informes/DEV-HU-02.md`

No se tocaron `backend/tests/**`, `frontend/tests/**`, `frontend/dist` ni los archivos de paquete de
la raíz.
