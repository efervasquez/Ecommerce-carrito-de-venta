# CONTRATO — HU-02 Recuperación de contraseña

**Tipo:** Feature  
**Versión:** v1  
**Estado:** Aprobado (2026-11-23, usuario humano)  
**Origen:** `HUs/HU-02-recuperacion-de-contrasena.md`

---

## Paquete de contexto

| Fuente | Por qué entra |
|---|---|
| `HUs/HU-02-recuperacion-de-contrasena.md` | Historia, criterios de aceptación y escenarios Gherkin. |
| `TECH-DESIGN.md` §Criterios de aceptación por flujo | Link de un solo uso, expiración, cooldown, rate limit y protección de logs. |
| `adrs/0017-tokens-seguridad.md` | Token opaco UUID v4, SHA-256, tipo `recuperacion`, expiración de 1 hora, cooldown de 15 minutos, máximo 3 solicitudes diarias e invalidación de tokens previos. |
| `adrs/0018-transporte-smtp.md` | Evento de correo en `email.auth` y envío mediante relay transaccional. |
| `adrs/0004-contratos-api.md` | REST JSON `/api/v1`, Pydantic/OpenAPI y autenticación existente. |
| `adrs/0007-broker-workers.md` | Desacoplamiento del correo mediante RabbitMQ y cola durable. |
| `adrs/0019-seguridad-perimetral-iis.md` | Rate limit de 3 solicitudes por minuto por IP para endpoints de auth. |
| `contratos/CONTRATO-HU-01.md` | Convenciones ya aprobadas de auth: prefijo API, formato de mensajes, token y pantalla de login. |

## Interfaz observable

- API REST HTTP para solicitar y completar la recuperación.
- Evento RabbitMQ en la cola `email.auth`.
- Pantallas SPA `/login`, `/recuperar` y `/restablecer`.

## Comportamiento

### Solicitud de recuperación

**Entrada**

```http
POST /api/v1/auth/recuperar
Content-Type: application/json

{"email":"cliente.activo@ejemplo.com"}
```

**Casos**

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| Email existente | Email de una cuenta activa | HTTP 200 `{"message":"Si el email existe, recibirás un correo"}`; genera token `recuperacion` y publica evento en `email.auth`. | HU-02 criterio 2; ADR-0017 §Protección contra enumeración |
| Email inexistente | Email con formato válido no registrado | HTTP 200 con exactamente el mismo JSON y timing del caso anterior; no revela existencia ni publica evento. | ADR-0017 §Protección contra enumeración |
| Cooldown activo | Email con token enviado hace menos de 15 minutos | HTTP 200 con el mismo JSON; no genera token nuevo ni publica evento. | ADR-0017 §Throttling y Cooldown |
| Límite diario | Más de 3 solicitudes en 24 horas para la misma cuenta | HTTP 200 con el mismo JSON; no genera token nuevo ni publica evento. | ADR-0017 §Throttling y Cooldown |
| Email inválido | Cadena sin formato de correo válido | HTTP 422 `{"detail":"Formato de correo electrónico inválido"}`. | HU-02 supuesto de validación; convención HU-01 |
| Payload vacío o campo ausente | `{}` o payload sin `email` | HTTP 422 indicando campo requerido. | ADR-0004; convención HU-01 |
| Rate limit por IP | Más de 3 POST de auth por minuto desde la misma IP | HTTP 429 `{"detail":"Demasiadas solicitudes. Por favor, intente nuevamente en unos minutos."}`. | ADR-0019; convención HU-01 |

### Evento de recuperación

**Entrada:** publicación interna posterior a una solicitud válida para email existente.

**Casos**

| Caso | Salida esperada | Origen |
|---|---|---|
| Evento publicado | Cola durable `email.auth`; evento `auth.recuperacion_solicitada` con `correlation_id`, `timestamp` y payload `{email, token, url_recuperacion, expira_en}`. El token es UUID v4 crudo solo dentro del evento. | ADR-0017 §Flujo de recuperación; ADR-0018 tipos de correo; ADR-0007 |
| Cooldown o límite diario | No se publica evento adicional. | ADR-0017 §Throttling y Cooldown |

### Restablecimiento de contraseña

**Entrada**

```http
POST /api/v1/auth/restablecer
Content-Type: application/json

{"token":"<uuid-v4>","password":"MiClaveSegura2026!"}
```

**Casos**

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| Token válido y contraseña fuerte | Token `recuperacion`, no usado, con expiración futura | HTTP 200 con mensaje de confirmación; actualiza el hash, marca `usado_en` e invalida tokens de recuperación previos. | HU-02 criterios 3 y 4; ADR-0017 §Flujo de recuperación |
| Token reutilizado | Token con `usado_en` no nulo | HTTP 400 con mensaje genérico de enlace inválido/expirado; no cambia la contraseña. | HU-02 escenario 2; ADR-0017 |
| Token expirado | Token con `expira_en <= NOW()` | HTTP 400 con el mismo mensaje genérico; no cambia la contraseña. | HU-02 criterio 5; ADR-0017 |
| Token inexistente o alterado | UUID inexistente o token no UUID | HTTP 400 con el mismo mensaje genérico; no revela si existió. | ADR-0017 §Flujo de recuperación |
| Contraseña débil | Menos de 8 caracteres o sin mayúscula, minúscula y número | HTTP 422 con el mensaje de complejidad; el token permanece sin usar. | Convención DP-2 de HU-01 |
| Payload vacío o campo ausente | `{}` o sin `token`/`password` | HTTP 422 indicando campo requerido. | ADR-0004 |

### Interfaz web

| Pantalla | Ruta | Elementos observables | Comportamiento | Origen |
|---|---|---|---|---|
| Login | `/login` | Enlace visible `¿Olvidaste tu contraseña?` | Navega a `/recuperar`. | HU-02 criterio 1 |
| Solicitud | `/recuperar` | Input `email`; botón **propuesto** `Enviar enlace` | En éxito muestra el mensaje genérico; no muestra si el email existe. | HU-02 criterio 1; ADR-0017 |
| Restablecimiento | `/restablecer?token=<token>` | Inputs `password`, `confirm_password`; botón `Actualizar contraseña` | Token válido permite confirmar; éxito muestra confirmación y enlaza a `/login`. | HU-02 criterios 3 y 4; escenario 1 |
| Enlace inválido | `/restablecer?token=<token>` | Pantalla informativa y botón **propuesto** `Solicitar nuevo enlace` | Bloquea el formulario y navega a `/recuperar`. | HU-02 criterio 5; escenario 2 |

## Nombres que no se negocian

| Tipo | Valor exacto |
|---|---|
| Ruta API propuesta | `POST /api/v1/auth/recuperar` |
| Ruta API propuesta | `POST /api/v1/auth/restablecer` |
| Ruta frontend propuesta | `/recuperar` |
| Ruta frontend propuesta | `/restablecer?token=<token>` |
| Campo | `email` |
| Campo | `token` |
| Campo | `password` |
| Campo | `confirm_password` |
| Cola | `email.auth` |
| Evento | `auth.recuperacion_solicitada` |
| Campo de evento | `url_recuperacion` |
| Mensaje propuesto | `Si el email existe, recibirás un correo` |
| Mensaje de contraseña | `La contraseña debe tener al menos 8 caracteres e incluir mayúsculas, minúsculas y números.` |
| Botón | `Actualizar contraseña` |
| Enlace de login | `¿Olvidaste tu contraseña?` |

## Rutas de cada rol

| Rol | Rutas | Origen |
|---|---|---|
| TESTER | `backend/tests/**`, `frontend/tests/**`, `frontend/src/**/*.test.tsx`, `frontend/src/**/*.spec.ts` | `AGENTS.md` |
| DEV | `backend/src/**`, `backend/alembic/**`, `backend/requirements*`, `backend/.env.example`, `frontend/src/**` excepto tests, `frontend/package*.json`, `infra/**` | `AGENTS.md` |
| LEAD | `contratos/**`, `informes/**` | `AGENTS.md` / proceso LEAD |

## Avisos de contexto

- Deuda en la zona del cambio: no existe `DEUDA.md` registrado; no se identifica deuda formal aplicable.
- Patrón a imitar: `backend/src/modules/auth/` de HU-01, incluyendo capas Router → Service → Repository,
  tokens opacos y publicación no bloqueante en `email.auth`.
- HU-02 depende de HU-01, que ya está aprobada e implementada.

## Decisiones propuestas (no venían fijadas con valor exacto en la HU)

| # | Decisión | Por qué hace falta | Estado |
|---|---|---|---|
| 1 | Ruta API `POST /api/v1/auth/recuperar` | ADR-0017 nombra la ruta; fija el endpoint observable. | Aprobada por usuario humano |
| 2 | Ruta API `POST /api/v1/auth/restablecer` | La HU exige una operación de cambio, pero no nombra la ruta. | Aprobada por usuario humano |
| 3 | Rutas frontend `/recuperar` y `/restablecer?token=` | La HU describe pantallas, pero no fija sus URLs. | Aprobada por usuario humano |
| 4 | Mensaje genérico `Si el email existe, recibirás un correo` | ADR-0017 fija el contenido conceptual, pero el contrato necesita valor textual. | Aprobada por usuario humano |
| 5 | Evento `auth.recuperacion_solicitada` y campo `url_recuperacion` | El ADR fija la cola y el tipo de correo, pero no estos nombres exactos. | Aprobada por usuario humano |
| 6 | Botón `Enviar enlace` y botón `Solicitar nuevo enlace` | La HU solo fija `Actualizar contraseña`; se necesitan nombres observables para probar las pantallas. | Aprobada por usuario humano |

## Fuera del contrato (decide el DEV)

- Estructura interna, nombres de funciones, repositorios y consultas SQL.
- Algoritmo concreto de hash de contraseña, manteniendo la política aprobada.
- Proveedor concreto del relay dentro de Brevo/SendGrid y detalles del worker.
- Estilos visuales, siempre que se respeten rutas, campos, textos y estados observables.

## Preguntas abiertas para el humano

Ninguna. El usuario aprobó las decisiones propuestas 1–6 y la redirección a `/login` después del cambio exitoso.

## Changelog

| Versión | Fecha | Cambio | Motivo | Aprobado por |
|---|---|---|---|---|
| v1 | 2026-11-23 | Versión inicial y aprobación de decisiones observables | Inicio de HU-02 | Usuario humano |
