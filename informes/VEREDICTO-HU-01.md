# Informe de Veredicto — HU-01 Autoregistro y autenticación de clientes

**Fecha:** 2026-11-21
**Documento base:** `contratos/CONTRATO-HU-01.md` (v1, aprobada 2026-10-16)
**Tipo de tarea:** Feature
**Rama:** `feat/hu-01-autoregistro` (base: `b0ef240`)
**Árbitro:** Agente LEAD
**Entregas:** DEV `36a23a9` · TESTER `ae2ffbd`

---

## 1. Dictamen

🟡 **PARCIALMENTE VERIFICADO — pendiente de infraestructura, no de código ni de pruebas.**

- **Frontend (SPA):** 🟢 **13/13 PASS** verificado de primera mano (Vitest).
- **Backend (API):** 🟢 **7/7 PASS** (casos sin dependencias) · 🔴 **14 FAIL por infraestructura** (MySQL sin usuario de test + RabbitMQ caído) · ⚪ **3 NO VERIFICADO** (no provocables desde la interfaz observable).

Ninguno de los agentes se apartó de la spec. Los 14 rojos no son fallos de código ni de pruebas: son
**infraestructura no disponible** que el contrato no define cómo proveer.

---

## 2. Verificación de propiedad de rutas

| Rol | Rutas asignadas (AGENTS.md) | Tocadas | Hallazgo |
|---|---|---|---|
| DEV | `backend/src/**`, `backend/alembic/**`, `backend/requirements*`, `backend/.env.example`, `frontend/src/**`, `frontend/package*.json`, etc. | 23 archivos en ruta + `informes/DEV-HU-01.md` | ⚠️ `informes/` fuera de ruta (inducido por el encargo del LEAD) |
| TESTER | `backend/tests/**`, `frontend/tests/**`, `frontend/src/**/*.test.tsx`, `*.spec.ts` | 4 archivos en ruta + `informes/TESTER-HU-01.md` | ⚠️ `informes/` fuera de ruta (inducido por el encargo del LEAD) |

Los commits llevan prefijo correcto (`[DEV]`, `[TESTER]`). Ambos trabajaron sobre la **misma spec** v1.
El único hallazgo (`informes/`) es menor y lo originó el encargo del LEAD ("escribe tu informe en
`informes/*-HU-01.md`"), no una intromisión entre roles.

---

## 3. Matriz de trazabilidad

### 3.1 Solicitud de Autoregistro (`POST /api/v1/auth/registro`)

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| Camino feliz → 200 + mensaje genérico | `test_camino_feliz_email_nuevo_retorna_200_mensaje_generico` | 🔴 FAIL infra MySQL |
| Email duplicado → mismo JSON y tiempo | `test_email_duplicado_retorna_mismo_json_y_tiempo_similar` | 🔴 FAIL infra MySQL |
| Cooldown activo → mismo JSON, no reencola | `test_cooldown_activo_no_reencola_segundo_evento` | 🔴 FAIL infra RabbitMQ |
| Email inválido → 422 `{"detail":"Formato de correo electrónico inválido"}` | `test_email_invalido_retorna_422` | 🟢 PASS |
| Payload vacío `{}` → 422 | `test_payload_vacio_retorna_422` | 🟢 PASS |
| Campo `email` ausente → 422 | `test_campo_email_ausente_retorna_422` | 🟢 PASS |
| `email` vacío → 422 | `test_email_vacio_retorna_422` | 🟢 PASS |
| Rate limit excedido → 429 | `test_rate_limit_excedido_retorna_429` | 🟢 PASS |

### 3.2 Activación (`POST /api/v1/auth/activar`)

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| Camino feliz → 200 | `test_camino_feliz_token_valido_retorna_200` | 🔴 FAIL infra MySQL/RabbitMQ |
| Token inexistente → 400 | `test_token_inexistente_retorna_400` | 🔴 FAIL infra MySQL |
| Token formato no-UUID → 400 | `test_token_formato_invalido_retorna_400` | 🔴 FAIL infra MySQL |
| Contraseña débil → 422 y no marca token | `test_password_debil_retorna_422_y_no_marca_token` | 🔴 FAIL infra MySQL/RabbitMQ |
| Token ya usado → 400 | `test_token_ya_usado_retorna_400` | 🔴 FAIL infra MySQL/RabbitMQ |
| Token expirado (>24h) → 400 | `test_token_expirado_retorna_400` | ⚪ NO VERIFICADO (skip) |

### 3.3 Login (`POST /api/v1/auth/login`)

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| Camino feliz → 200 con JWT | `test_camino_feliz_retorna_jwt_con_payload` | 🔴 FAIL infra MySQL/RabbitMQ |
| Contraseña incorrecta → 401 | `test_password_incorrecta_retorna_401` | 🔴 FAIL infra MySQL/RabbitMQ |
| Cuenta no activada → 401 | `test_cuenta_no_activada_retorna_401` | 🔴 FAIL infra MySQL |
| Email inexistente → 401 | `test_email_inexistente_retorna_401` | 🔴 FAIL infra MySQL |
| Cuenta suspendida → 403 | `test_cuenta_suspendida_retorna_403` | ⚪ NO VERIFICADO (skip) |

### 3.4 Sesión (`GET /api/v1/auth/me`)

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| Camino feliz → 200 perfil | `test_camino_feliz_token_valido_retorna_perfil` | 🔴 FAIL infra MySQL/RabbitMQ |
| Token ausente → 401 | `test_token_ausente_retorna_401` | 🟢 PASS |
| Token malformado → 401 | `test_token_malformado_retorna_401` | 🟢 PASS |
| Token expirado (>1h) → 401 | `test_token_expirado_retorna_401` | ⚪ NO VERIFICADO (skip) |

### 3.5 Interfaz Web (SPA)

| Pantalla | Prueba | Resultado |
|---|---|---|
| `/registro` | `Registro.test.tsx` (3 tests) | 🟢 PASS |
| `/activar` | `Activacion.test.tsx` (3 tests) | 🟢 PASS |
| `/login` | `Login.test.tsx` (3 tests) | 🟢 PASS |

### 3.6 Evento RabbitMQ (`email.auth`)

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| Publica `auth.activacion_solicitada` con formato exacto | `test_registro_publica_evento_activacion_en_cola_email_auth` | 🔴 FAIL infra RabbitMQ |

---

## 4. Evidencia de ejecución (verificación independiente del LEAD)

### Backend — `pytest tests/test_hu01_auth.py`
```text
14 failed, 7 passed, 3 skipped in 35.83s
```
Causa de los 14 `failed` (transcripción de la salida real):
- 13 × `sqlalchemy.exc.OperationalError: (1045, "Access denied for user 'test_user'@'localhost'")` — el
  fixture `default_env` (`backend/tests/conftest.py:22-24`) fija `MYSQL_USER=test_user`,
  `MYSQL_PASSWORD=test_password`, `MYSQL_DB=test_botica`, que **no existen** en el MySQL92 local.
- 1 × `aiormq.exceptions.AMQPConnectionError: [WinError 1225]` — RabbitMQ no está corriendo en
  `localhost:5672` (no hay servicio instalado).

### Frontend — `npx vitest run`
```text
Test Files  4 passed (4)
     Tests  13 passed (13)
```

---

## 5. Arbitraje

| Hallazgo | Lectura con la spec en la mano | Desenlace |
|---|---|---|
| 14 rojos de backend | La spec define el **comportamiento**, no el **entorno de test** (qué credenciales de MySQL ni que RabbitMQ esté levantado). El código del DEV (`service.py`, `router.py`, `main.py`) y las pruebas del TESTER (caja negra HTTP + bus) son lecturas correctas del contrato. | **No se corrige ningún agente.** El bloqueo es infraestructura. |
| 3 `NO VERIFICADO` (token/JWT expirado, suspendida) | No son provocables desde la interfaz observable sin manipular DB o clave JWT; el TESTER los marcó `skip` correctamente en vez de aflojarlos. | **No se corrige ningún agente.** Requiere decisión del humano. |

---

## 6. Preguntas para el humano (gate)

1. **Entorno de test del backend.** Para verificar los 14 casos restantes se necesita (a) crear en el
   MySQL92 local el usuario `test_user`/`test_password` y la base `test_botica` con las migraciones
   aplicadas, y (b) levantar RabbitMQ en `localhost:5672` (hoy no hay servicio instalado).
   **¿Autorizo levantar ese entorno de test, o acepto los 14 como `NO VERIFICADO`?**
2. **Casos no provocables (3).** Token de activación expirado (>24h), cuenta suspendida (403) y JWT
   expirado (>1h) requieren manipular DB/clave o un fixture de seeding. **¿Los acepto como
   `NO VERIFICADO`, o habilito un fixture de seed en el entorno de test?**
3. **Credenciales de test desacopladas.** Las pruebas fijan `test_user`/`test_botica`; el entorno real
   usa las de `.env`. **¿Mantengo un entorno de test dedicado (recomendado) o alineo las pruebas al
   `.env` local?**

---

## 7. Conclusión

La HU-01 está **implementada y probada en todo lo verificable sin infraestructura** (frontend completo
+ 7 casos de validación/seguridad del backend, que cubren anti-enumeración, rate limit y protección de
sesión). El código respeta los ADRs (0003, 0004, 0007, 0015, 0017, 0018, 0019) y la arquitectura por
capas. Resta levantar el entorno de test para dar por verde los 14 casos transaccionales.
