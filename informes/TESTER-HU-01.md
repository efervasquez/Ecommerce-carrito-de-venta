# Informe de Entrega — TESTER (HU-01)

**Unidad:** HU-01 — Autoregistro rápido y autenticación de clientes (tipo: FEATURE)
**Documento base:** `contratos/CONTRATO-HU-01.md` (v1, aprobada 2026-10-16)
**Rama:** `feat/hu-01-autoregistro`
**Autor:** Agente TESTER
**Fecha:** 2026-11-21

---

## 1. Resumen

Se escribieron pruebas de **caja negra** contra la interfaz observable del contrato
(API REST `/api/v1/auth/*`, bus de eventos RabbitMQ cola `email.auth` y pantallas SPA
`/registro`, `/activar`, `/login`). No se importó ninguna función, clase o servicio interno
del DEV: las pruebas solo envían HTTP y leen el JSON de respuesta (backend) o renderizan
la pantalla y verifican los elementos observables del contrato (frontend).

Resultado de la ejecución contra el árbol actual (DEV ya commitó la HU-01 en `36a23a9`):

| Capa | Resultado |
|---|---|
| **Frontend** (SPA) | 🟢 **13/13 PASS** — el DEV satisface todos los elementos observables del contrato |
| **Backend** (API) | 7 PASS · 14 FAIL (por infraestructura, no por la prueba) · 3 NO VERIFICADO |

Detalle de los fallos de backend: **14 casos requieren infraestructura** y hoy fallan por
entorno, no por la prueba — MySQL responde `Access denied` para las credenciales de test y
RabbitMQ no está corriendo (`Connection refused` en `localhost:5672`). Los **7 casos verdes**
son los de validación sin dependencias (email/payload inválidos, rate limit y `/me` sin token),
lo que demuestra que el DEV ya implementó correctamente esa parte del contrato.

---

## 2. Matriz de Cobertura del Contrato

### 3.1 Solicitud de Autoregistro (`POST /api/v1/auth/registro`)

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| Camino feliz (email nuevo → 200 + mensaje genérico) | `test_camino_feliz_email_nuevo_retorna_200_mensaje_generico` | 🔴 FAIL (infra MySQL) |
| Email duplicado → mismo JSON y tiempo | `test_email_duplicado_retorna_mismo_json_y_tiempo_similar` | 🔴 FAIL (infra MySQL) |
| Cooldown activo → mismo JSON, no reencola | `test_cooldown_activo_no_reencola_segundo_evento` | 🔴 FAIL (infra RabbitMQ) |
| Email inválido → 422 `{"detail":"Formato de correo electrónico inválido"}` | `test_email_invalido_retorna_422` | 🟢 PASS |
| Payload vacío `{}` → 422 | `test_payload_vacio_retorna_422` | 🟢 PASS |
| Campo `email` ausente → 422 | `test_campo_email_ausente_retorna_422` | 🟢 PASS |
| `email` vacío → 422 | `test_email_vacio_retorna_422` | 🟢 PASS |
| Rate limit excedido (>3/min/IP) → 429 | `test_rate_limit_excedido_retorna_429` | 🟢 PASS |

### 3.2 Activación de Cuenta (`POST /api/v1/auth/activar`)

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| Camino feliz (token válido + password fuerte → 200) | `test_camino_feliz_token_valido_retorna_200` | 🔴 FAIL (infra MySQL/RabbitMQ) |
| Token inexistente → 400 | `test_token_inexistente_retorna_400` | 🔴 FAIL (infra MySQL) |
| Token formato no-UUID/alterado → 400 | `test_token_formato_invalido_retorna_400` | 🔴 FAIL (infra MySQL) |
| Contraseña débil → 422 y no marca token | `test_password_debil_retorna_422_y_no_marca_token` | 🔴 FAIL (infra MySQL/RabbitMQ) |
| Token ya usado → 400 | `test_token_ya_usado_retorna_400` | 🔴 FAIL (infra MySQL/RabbitMQ) |
| Token expirado (>24 h) → 400 | `test_token_expirado_retorna_400` | ⚪ NO VERIFICADO (skip) |

### 3.3 Autenticación / Login (`POST /api/v1/auth/login`)

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| Camino feliz → 200 con `access_token`/`token_type`/`expires_in`/`usuario` | `test_camino_feliz_retorna_jwt_con_payload` | 🔴 FAIL (infra MySQL/RabbitMQ) |
| Contraseña incorrecta → 401 | `test_password_incorrecta_retorna_401` | 🔴 FAIL (infra MySQL/RabbitMQ) |
| Cuenta no activada → 401 (mismo mensaje) | `test_cuenta_no_activada_retorna_401` | 🔴 FAIL (infra MySQL) |
| Email inexistente → 401 (mismo mensaje) | `test_email_inexistente_retorna_401` | 🔴 FAIL (infra MySQL) |
| Cuenta suspendida → 403 | `test_cuenta_suspendida_retorna_403` | ⚪ NO VERIFICADO (skip) |

### 3.4 Inspección de Sesión (`GET /api/v1/auth/me`)

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| Camino feliz → 200 `{id,email,rol,estado}` | `test_camino_feliz_token_valido_retorna_perfil` | 🔴 FAIL (infra MySQL/RabbitMQ) |
| Token ausente → 401 | `test_token_ausente_retorna_401` | 🟢 PASS |
| Token malformado → 401 | `test_token_malformado_retorna_401` | 🟢 PASS |
| Token expirado (>1 h) → 401 | `test_token_expirado_retorna_401` | ⚪ NO VERIFICADO (skip) |

### 3.5 Interfaz Web (SPA React)

| Pantalla | Prueba (archivo) | Resultado |
|---|---|---|
| `/registro` — input `email`, botón "Registrarme", éxito/error | `frontend/tests/Registro.test.tsx` (3 tests) | 🟢 PASS |
| `/activar` — inputs `password`/`confirm_password`, botón "Activar cuenta", token del query | `frontend/tests/Activacion.test.tsx` (3 tests) | 🟢 PASS |
| `/login` — inputs `email`/`password`, botón "Iniciar sesión", error ante 401 | `frontend/tests/Login.test.tsx` (3 tests) | 🟢 PASS |

### 3.6 Evento de Correo en RabbitMQ

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| Publica evento `auth.activacion_solicitada` en cola `email.auth` con formato exacto | `test_registro_publica_evento_activacion_en_cola_email_auth` | 🔴 FAIL (infra RabbitMQ) |

### Sección 4 — Nombres que no se negocian (verificación textual)

Los siguientes nombres se verifican **textualmente** en las pruebas (rutas API, cola, evento,
campos de payload, mensajes visibles y textos de botón):

- Rutas API `POST /api/v1/auth/{registro,activar,login}` y `GET /api/v1/auth/me`.
- Cola `email.auth` y evento `auth.activacion_solicitada` (`test_registro_publica_evento_...`).
- Campos `email`, `token`, `password`, `access_token`, `expires_in` (asertados en payloads).
- Mensajes: `"Si el correo ingresado es válido, recibirás un enlace de activación en tu buzón."`,
  `"Cuenta activada exitosamente. Ya puedes iniciar sesión."`, `"El enlace de activación es inválido o ha expirado."`,
  `"Credenciales inválidas o cuenta no activada."`, `"No autenticado o token inválido."`,
  `"Demasiadas solicitudes. Por favor, intente nuevamente en unos minutos."`,
  `"La contraseña debe tener al menos 8 caracteres e incluir mayúsculas, minúsculas y números."`.
- Botones `"Registrarme"`, `"Activar cuenta"`, `"Iniciar sesión"` (`getByRole('button', { name })`).

---

## 3. Evidencia de Ejecución

### Backend (`pytest backend/tests/test_hu01_auth.py`)

```text
14 failed, 7 passed, 3 skipped in 31.63s
```

- **7 passed**: `test_email_invalido_retorna_422`, `test_payload_vacio_retorna_422`,
  `test_campo_email_ausente_retorna_422`, `test_email_vacio_retorna_422`,
  `test_rate_limit_excedido_retorna_429`, `test_token_ausente_retorna_401`,
  `test_token_malformado_retorna_401`.
- **14 failed** por infraestructura (no por la prueba): `Access denied` de MySQL (credenciales de
  test no coinciden) y `Connection refused` de RabbitMQ.
- **3 skipped** (`NO VERIFICADO`): token de activación expirado, cuenta suspendida, JWT expirado.

### Frontend (`npm test` en `frontend/`)

```text
Test Files  4 passed (4)
Tests       13 passed (13)
```

Los 9 tests de HU-01 (3 por pantalla) pasan en verde contra la implementación del DEV.

---

## 4. Decisiones de diseño de la suite

1. **IP de origen única por test.** El contrato fija 3 req/min **por IP** (ADR-0019) y el DEV lo
   implementó a nivel de aplicación. Para que cada test parta de un presupuesto limpio e
   independiente, el fixture `auth_client` ejecuta cada test desde una IP distinta
   (`ASGITransport(client=(host, 50000))`). Sigue siendo caja negra: solo se varía la IP del request.
2. **El caso de rate limit se prueba con emails inválidos** (validación Pydantic, sin tocar DB) para
   aislar el comportamiento 429 de la infraestructura de datos.
3. **Casos no provocables desde fuera** (`NO VERIFICADO`) quedan con `@pytest.mark.skip` y un
   `reason` explícito, en lugar de aflojar la prueba o tocar código del DEV.

---

## 5. Hallazgos / Preguntas para el LEAD

1. **Infraestructura requerida para el verde del backend.** Los 14 casos pendientes pasarán cuando
   exista MySQL corriendo con credenciales que coincidan con el entorno de test (`test_user` /
   `test_password`, o las que el entorno fije) y RabbitMQ en `localhost:5672`. El paquete
   `cryptography` ya está disponible en el `.venv`.
2. **Coexistencia del rate limiter con la suite.** El rate limiter de aplicación (3/min/IP) es una
   barrera para cualquier suite de integración que haga más de 3 peticiones a `/api/v1/auth/*`.
   Esta suite lo sortea con IP por test; ¿debe el DEV proveer un modo test (deshabilitar/ampliar el
   límite cuando `ENVIRONMENT=testing`)?
3. **3 casos `NO VERIFICADO`** (token expirado, cuenta suspendida, JWT expirado) no son provocables
   desde la interfaz observable sin manipular la DB o la clave JWT. El LEAD debe decidir si se
   aceptan como `NO VERIFICADO` o si se habilita un fixture de seeding en el entorno de test.

---

## 6. Commits del TESTER

Solo rutas propiedad de TESTER + informe solicitado:

- `backend/tests/test_hu01_auth.py`
- `frontend/tests/Registro.test.tsx`
- `frontend/tests/Activacion.test.tsx`
- `frontend/tests/Login.test.tsx`
- `informes/TESTER-HU-01.md`
