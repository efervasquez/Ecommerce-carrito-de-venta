# Informe de Veredicto — HU-02 Recuperación de contraseña

**Fecha:** 2026-11-23  
**Documento base:** `contratos/CONTRATO-HU-02.md` v1, aprobado por usuario humano  
**Tipo:** Feature  
**Rama:** `feat/hu-02-recuperacion`  
**Entregas:** TESTER `ac2d984`, `02c886f`; DEV `ba38e1a`  
**Árbitro:** LEAD

## 1. Dictamen

🟢 **APROBADO con 2 casos `NO VERIFICADO` aceptados por el humano.**

- Backend HU-02: **14 PASS, 2 NO VERIFICADO**.
- Frontend HU-02: **6/6 PASS**.
- Suite frontend completa: **19/19 PASS**.

No quedan rojos. Los dos casos pendientes requieren avanzar el reloj o manipular directamente la
base de datos; el TESTER los dejó explícitamente como `skip` y no debilitó las pruebas.

## 2. Propiedad y spec

- Ambos agentes trabajaron sobre `contratos/CONTRATO-HU-02.md` v1.
- DEV: código en rutas DEV y `informes/DEV-HU-02.md`; commit `ba38e1a`.
- TESTER: pruebas en rutas TESTER y `informes/TESTER-HU-02.md`; commits `ac2d984` y `02c886f`.
- Los informes están fuera de las rutas operativas y fueron solicitados explícitamente por el LEAD.
- No se tocaron los artefactos raíz no relacionados (`package.json`, `package-lock.json`).

## 3. Matriz de trazabilidad backend

| Caso | Prueba | Resultado |
|---|---|---|
| Email existente: 200, mensaje y evento | `test_email_existente_retorna_200_mensaje_y_publica_evento` | 🟢 PASS |
| Email inexistente: mismo JSON y timing | `test_email_inexistente_retorna_mismo_json_y_timing_similar` | 🟢 PASS |
| Cooldown: no publica evento adicional | `test_cooldown_no_publica_evento_adicional` | 🟢 PASS |
| Límite diario: no cuarta publicación | `test_limite_diario_tres_solicitudes_no_publica_una_cuarta` | ⚪ NO VERIFICADO |
| Email inválido | `test_email_invalido_retorna_422` | 🟢 PASS |
| Payload/campo ausente | `test_payload_vacio_retorna_422`, `test_campo_email_ausente_retorna_422` | 🟢 PASS |
| Rate limit por IP | `test_rate_limit_por_ip_retorna_429` | 🟢 PASS |
| Evento durable y payload exacto | `test_evento_durable_tiene_nombre_y_payload_exactos` | 🟢 PASS |
| Token válido y password fuerte | `test_token_valido_password_fuerte_retorna_200` | 🟢 PASS |
| Token reutilizado | `test_token_reutilizado_retorna_400_con_mensaje_generico` | 🟢 PASS |
| Token expirado | `test_token_expirado_retorna_400_mismo_mensaje` | ⚪ NO VERIFICADO |
| Token inexistente/alterado | `test_token_inexistente_o_alterado_retorna_400_mismo_mensaje` | 🟢 PASS |
| Password débil conserva token | `test_password_debil_retorna_422_y_token_permanece_sin_usar` | 🟢 PASS |
| Payload inválido en restablecer | pruebas de payload vacío y campos ausentes | 🟢 PASS |

Ejecución independiente:

```text
14 passed, 2 skipped in 16.71s
```

## 4. Matriz de trazabilidad frontend

| Pantalla | Pruebas | Resultado |
|---|---|---|
| `/login` enlace `¿Olvidaste tu contraseña?` | `HU02Login.test.tsx` | 🟢 PASS |
| `/recuperar` input, botón, POST y mensaje | `Recuperar.test.tsx` | 🟢 PASS |
| `/restablecer` campos, token, éxito y estado inválido | `Restablecer.test.tsx` | 🟢 PASS |

Suite completa frontend:

```text
Test Files  7 passed (7)
Tests       19 passed (19)
```

## 5. Arbitraje

| Hallazgo | Desenlace |
|---|---|
| Estado inválido inicialmente esperado sin petición | Se apartó la prueba. TESTER corrigió el flujo para provocar el 400 mediante POST en `02c886f`; ahora PASS. |
| Límite diario | `NO VERIFICADO`: cooldown de 15 minutos impide probar tres solicitudes diarias sin reloj/DB controlados. No se corrige ningún agente. |
| Token expirado | `NO VERIFICADO`: requiere esperar una hora o manipular reloj/DB. No se corrige ningún agente. |

## 6. Gate resuelto

El usuario aceptó los dos casos `NO VERIFICADO` —límite diario y token expirado— el 2026-11-23.
HU-02 queda cerrada como aprobada localmente.

## 7. Archivos relevantes

- `contratos/CONTRATO-HU-02.md`
- `backend/src/modules/auth/service.py`
- `frontend/src/pages/Recuperar.tsx`
- `frontend/src/pages/Restablecer.tsx`
- `backend/tests/test_hu02_password_recovery.py`
- `frontend/tests/Recuperar.test.tsx`
- `frontend/tests/Restablecer.test.tsx`
