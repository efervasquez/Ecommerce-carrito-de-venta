# Informe de Entrega — TESTER (HU-02)

**Unidad:** HU-02 — Recuperación de contraseña (FEATURE)
**Documento base:** `contratos/CONTRATO-HU-02.md` (v1, aprobada 2026-11-23)
**Rama:** `feat/hu-02-recuperacion`
**Autor:** Agente TESTER

## 1. Entrega

Se escribieron pruebas de caja negra para:

- `POST /api/v1/auth/recuperar` y sus validaciones, anti-enumeración, cooldown, rate limit y evento RabbitMQ.
- `POST /api/v1/auth/restablecer` y sus casos de token/password.
- Frontend `/login`, `/recuperar` y `/restablecer?token=...`.

Las pruebas no importan servicios internos de producción. El backend usa HTTP y RabbitMQ como
interfaces observables; el frontend verifica DOM, rutas, payloads y mensajes del contrato.

## 2. Matriz Backend

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| Email existente: 200, mensaje y evento | `test_email_existente_retorna_200_mensaje_y_publica_evento` | PASS |
| Email inexistente: mismo JSON y timing | `test_email_inexistente_retorna_mismo_json_y_timing_similar` | PASS |
| Cooldown: no publica evento adicional | `test_cooldown_no_publica_evento_adicional` | PASS |
| Límite diario: no cuarta publicación | `test_limite_diario_tres_solicitudes_no_publica_una_cuarta` | NO VERIFICADO |
| Email inválido | `test_email_invalido_retorna_422` | PASS |
| Payload/campo ausente en recuperar | `test_payload_vacio_retorna_422`, `test_campo_email_ausente_retorna_422` | PASS |
| Rate limit por IP | `test_rate_limit_por_ip_retorna_429` | PASS |
| Evento durable, nombre y payload exactos | `test_evento_durable_tiene_nombre_y_payload_exactos` | PASS |
| Token válido y password fuerte | `test_token_valido_password_fuerte_retorna_200` | PASS |
| Token reutilizado | `test_token_reutilizado_retorna_400_con_mensaje_generico` | PASS |
| Token expirado | `test_token_expirado_retorna_400_mismo_mensaje` | NO VERIFICADO |
| Token inexistente/alterado | `test_token_inexistente_o_alterado_retorna_400_mismo_mensaje` | PASS |
| Password débil y token permanece usable | `test_password_debil_retorna_422_y_token_permanece_sin_usar` | PASS |
| Payload inválido en restablecer | `test_payload_vacio_retorna_422`, `test_payload_sin_token_o_password_retorna_422` | PASS |

### No verificados

- **Límite diario:** el cooldown de 15 minutos impide distinguirlo desde la interfaz observable sin avanzar el reloj o disponer de un mecanismo de test aprobado.
- **Token expirado:** requeriría esperar una hora o manipular reloj/DB, fuera de la interfaz observable.

## 3. Matriz Frontend

| Pantalla | Pruebas | Resultado |
|---|---|---|
| `/login` | Enlace exacto `¿Olvidaste tu contraseña?` hacia `/recuperar` | PASS |
| `/recuperar` | Input `email`, botón `Enviar enlace`, POST y mensaje genérico | ROJO: `src/pages/Recuperar` no resuelto |
| `/restablecer?token=...` | Campos, botón, token del query, éxito y estado inválido | ROJO: `src/pages/Restablecer` no resuelto |

## 4. Evidencia de Ejecución

### Backend

```text
14 passed, 2 skipped in 14.09s
```

Se observó únicamente el warning de cierre tardío de `aiomysql` al finalizar el proceso (`Event loop is closed`);
no altera el resultado de pytest.

### Frontend

```text
Test Files  1 passed | 2 failed
Tests       1 passed; Recuperar/Restablecer no recolectaron tests por imports no resueltos
```

El rojo frontend es el esperado mientras no existan las pantallas correspondientes. La prueba de `/login`
confirma el enlace exacto y su destino.

## 5. Archivos

- `backend/tests/test_hu02_password_recovery.py`
- `frontend/tests/HU02Login.test.tsx`
- `frontend/tests/Recuperar.test.tsx`
- `frontend/tests/Restablecer.test.tsx`
- `informes/TESTER-HU-02.md`
