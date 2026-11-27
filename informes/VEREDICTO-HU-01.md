# Informe de Veredicto — HU-01 Autoregistro y autenticación de clientes

**Fecha:** 2026-11-21
**Documento base:** `contratos/CONTRATO-HU-01.md` (v1, aprobada 2026-10-16)
**Tipo de tarea:** Feature
**Rama:** `feat/hu-01-autoregistro` (base: `b0ef240`)
**Árbitro:** Agente LEAD
**Entregas:** DEV `36a23a9` · TESTER `ae2ffbd`

---

## 1. Dictamen final

🟢 **APROBADO con 3 casos `NO VERIFICADO` aceptados por el humano.**

- **Frontend (SPA):** 🟢 **13/13 PASS** verificado de primera mano (Vitest).
- **Backend HU-01:** 🟢 **21/21 PASS** de los casos ejecutables · ⚪ **3 NO VERIFICADO** (no provocables desde la interfaz observable).

El bug de timing del DEV fue corregido en `b975160`; la prueba de anti-enumeración quedó verde.
El TESTER corrigió el aislamiento de loops y la durabilidad de `email.auth` en `7c1197b`.

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

### Backend HU-01 — `pytest tests/test_hu01_auth.py`
```text
21 passed, 3 skipped in 14.19s
```
La ejecución final usó MySQL `test_botica` migrado y RabbitMQ `rabbitmq:4` en Docker, publicado en
`localhost:5672`.

### Frontend — `npx vitest run`
```text
Test Files  4 passed (4)
     Tests  13 passed (13)
```

### Suite backend completa — `pytest tests/`

La suite global quedó bloqueada por un problema preexistente de aislamiento: los tests de configuración
de Sprint 0 dejan cacheado `MYSQL_HOST=192.168.1.100` mediante `get_settings()` y los tests posteriores
de HU-01 intentan conectarse a ese host. Esto no ocurre ejecutando la suite HU-01 de forma aislada y no
afecta el dictamen de los casos de HU-01, pero queda como deuda de integración de tests.

---

## 5. Arbitraje

| Hallazgo | Lectura con la spec en la mano | Desenlace |
|---|---|---|
| Timing del registro duplicado | La publicación síncrona bloqueaba ~4s con RabbitMQ caído; la spec exige mismo tiempo de respuesta. | **DEV corregido**, vuelta 1, `b975160`; `test_email_duplicado...` PASS. |
| Durabilidad de `email.auth` | El ADR-0007 exige colas duraderas; el helper del TESTER declaraba `durable=False`. | **TESTER corregido**, vuelta 2, `7c1197b`; todos los casos RabbitMQ PASS. |
| Aislamiento de loops | El loop por función dejaba pool/tareas entre tests; `session` elimina los 2 fallos de aislamiento. | **TESTER corregido**, `7c1197b`. |
| 3 `NO VERIFICADO` (token/JWT expirado, suspendida) | No son provocables desde la interfaz observable sin manipular DB o clave JWT; el TESTER los marcó `skip` correctamente en vez de aflojarlos. | **No se corrige ningún agente.** Requiere decisión del humano. |

---

## 6. Decisiones del gate

1. El humano autorizó levantar el entorno dedicado de test: MySQL `test_user`/`test_botica` y RabbitMQ
   en Docker.
2. El humano aceptó los tres casos no provocables como `NO VERIFICADO`.

---

## 7. Conclusión

La HU-01 está **aprobada**: backend 21/21 casos ejecutables y frontend 13/13 pruebas en verde. Los tres
casos restantes quedan explícitamente `NO VERIFICADO` por no ser provocables desde la interfaz observable.
El código respeta los ADRs 0003, 0004, 0007, 0015, 0017, 0018 y 0019, así como la arquitectura por capas.
