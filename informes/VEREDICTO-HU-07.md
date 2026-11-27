# Informe de Veredicto — HU-07 Pasarela de pagos Stripe Sandbox

**Fecha:** 2026-11-25
**Documento base:** `contratos/CONTRATO-HU-07.md` v1, aprobado por usuario humano
**Tipo:** Feature
**Rama:** `feat/hu-07-pasarela-pagos`
**Entregas:** TESTER `dc945c6`; DEV `0e22d63`
**Árbitro:** LEAD

## 1. Dictamen

**APROBADO.** Los 2 casos NO VERIFICADO fueron aceptados por el usuario humano (2026-11-25).

- Backend HU-07: **24 PASS / 2 SKIPPED (NO VERIFICADO)**.
- Frontend HU-07 (`Checkout.test.tsx`): **4/4 PASS**.
- Frontend suite completa: **11/11 archivos, 41/41 tests PASS**.
- Build TypeScript/Vite: **exitoso**.
- Regresión backend: HU-03+04+05 **25 PASS / 3 SKIPPED**; HU-01+HU-02 **35 PASS / 5 SKIPPED**.

## 2. Matriz backend (HU-07)

Ejecución: `pytest tests/test_hu07_pagos_pedidos.py` → `24 passed, 2 skipped`.

| Caso | Prueba | Resultado |
|---|---|---|
| Guest: reserva 24h, `requiere_autenticacion`, sin PaymentIntent | `test_guest_reserva_sin_payment_intent` | PASS |
| Autenticado: `payment_intent_id`/`client_secret`/`monto`/`PEN` | `test_autenticado_devuelve_payment_intent` | PASS |
| Carrito vacío → 409 | `test_carrito_vacio_retorna_409` | PASS |
| Endpoints de pago sin sesión → 401 | `test_endpoint_de_pago_sin_sesion_retorna_401` | PASS |
| Rate limit checkout por IP → 429 | `test_rate_limit_checkout_por_ip_retorna_429` | PASS |
| Guest con checkout activo → 409 | `test_guest_con_checkout_activo_retorna_409` | PASS |
| Dirección ajena rechazada | `test_direccion_ajena_es_rechazada` | PASS |
| Zonas activas | `test_zonas_activas` | PASS |
| Crear y listar direcciones | `test_crear_y_listar_direcciones` | PASS |
| Dirección incompleta → 422 | `test_direccion_incompleta_retorna_422` | PASS |
| Zona inexistente → 409 `Zona no disponible` | `test_zona_inexistente_retorna_409` | PASS |
| Webhook `succeeded`: pedido `Registrado`, vacía carrito, descuenta stock | `test_succeeded_crea_pedido_vacia_carrito_y_descuenta_stock` | PASS |
| Webhook `succeeded` duplicado: idempotente | `test_succeeded_duplicado_no_crea_segundo_pedido` | PASS |
| Firma inválida → 400 | `test_firma_invalida_retorna_400` | PASS |
| Firma ausente → 400 | `test_firma_ausente_retorna_400` | PASS |
| `payment_failed`: sin pedido, carrito intacto, reserva liberada | `test_payment_failed_no_crea_pedido_y_conserva_carrito` | PASS |
| `GET pagos/{pi}`: procesando | `test_pago_procesando_tras_checkout` | PASS |
| `GET pagos/{pi}`: rechazado | `test_pago_rechazado_tras_webhook` | PASS |
| `GET pagos/{pi}` ajeno → 404 | `test_pago_ajeno_retorna_404` | PASS |
| `GET pedidos/{numero}` propio y ajeno | `test_pedido_propio_y_ajeno` | PASS |
| `GET pedidos/{numero}` inexistente → 404 | `test_pedido_inexistente_retorna_404` | PASS |
| Inconsistencia física al confirmar → `incidencia_stock` | `test_incidencia_stock` | SKIPPED (NO VERIFICADO) |
| Stock insuficiente al checkout | `test_checkout_stock_insuficiente_no_contacta_stripe` | SKIPPED (NO VERIFICADO) |

### Casos NO VERIFICADO (aceptados por el usuario humano, 2026-11-25)

1. `test_incidencia_stock` — provocar una inconsistencia física de almacén al confirmar el webhook es inviable en caja negra; decisión 11 del contrato: se acepta como NO VERIFICADO y se cubre con prueba de integración del backend.
2. `test_checkout_stock_insuficiente_no_contacta_stripe` — forzar stock insuficiente justo en el checkout requiere una condición de carrera; el 409 por stock ya está cubierto en HU-05 (`test_cantidad_superior_al_stock_retorna_409`).

## 3. Matriz frontend

| Área | Resultado |
|---|---|
| `/checkout`: captura de entrega y botón `Pagar ahora` | PASS (4/4) |
| Pago exitoso: `Procesando pago...` → confirmación `#BL-...` + monto | PASS |
| Pago rechazado: mensajes exactos y carrito intacto | PASS |
| Resto de la suite (HU-01 a HU-05) | PASS |

Ejecución: `npx vitest run` → `Test Files 11 passed (11)`, `Tests 41 passed (41)`; `npm run build` → correcto.

## 4. Arbitraje

- **Primera entrega cruzada:** el TESTER escribió las pruebas solo desde el contrato (commits sin ver implementación) y reportó rojos esperados. El DEV implementó conforme al contrato y coordinó el secreto de webhook (`STRIPE_WEBHOOK_SECRET`, default `whsec_test`) y el formato `^BL-\d+$`.
- **Verificación independiente del LEAD:** HU-07 backend 24/2, frontend 4/4, suite completa 41/41, build OK, y regresión sin roturas.
- **Cambio de comportamiento de HU-05:** el checkout autenticado ahora crea PaymentIntent; el caso guest de HU-05 (solo reserva) se conserva y sigue verde.
- **Seguridad:** no se persisten ni loguean datos de tarjeta; solo identificadores de Stripe. `.env.example` usa placeholders (`sk_test_REEMPLAZAR`, `pk_test_REEMPLAZAR`, `whsec_REEMPLAZAR`); no hay secretos reales. La CSP de `backend/web.config` autoriza `https://js.stripe.com` (y `api.stripe.com`/`hooks.stripe.com`).
- **Deuda de infraestructura (preexistente, no bloquea):** la suite backend completa sigue sin correrse en un solo comando (configuración de pytest); se validó por módulos.

## 5. Propiedad de rutas

- TESTER: `backend/tests/test_hu07_pagos_pedidos.py`, `frontend/tests/Checkout.test.tsx`; commit `dc945c6`.
- DEV: `backend/src/modules/pagos/**`, `backend/src/modules/carrito/**`, `backend/alembic/versions/0003_*`, `backend/src/config.py`, `backend/src/main.py`, `backend/src/core/rate_limit.py`, `backend/.env.example`, `frontend/src/**`, `frontend/index.html`, `frontend/vite.config.ts`, `infra/seed-zonas.sql`, `informes/DEV-HU-07.md`; commit `0e22d63`.
- El commit del DEV no modificó archivos de prueba (verificado con `git diff 1afb8a6..HEAD -- backend/tests frontend/tests`: solo las pruebas del TESTER).
- LEAD: `contratos/CONTRATO-HU-07.md` (`1afb8a6`), veredicto.
- No se cometieron artefactos no rastreados (`frontend/dist`, `package.json` raíz, `package-lock.json`).
