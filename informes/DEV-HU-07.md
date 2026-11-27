# Informe de Entrega DEV — HU-07 Pasarela de pagos Stripe Sandbox

**Fecha:** 2026-11-25  
**Rol:** DEV  
**Documento base:** `contratos/CONTRATO-HU-07.md` v1 (aprobado)  
**Rama:** `feat/hu-07-pasarela-pagos`  
**Coordinación:** pruebas TESTER commit `dc945c6`.

## 1. Backend

### Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/zonas` | Zonas activas (auth). |
| GET / POST | `/api/v1/direcciones` | Direcciones del usuario (auth). |
| POST | `/api/v1/checkout` | Guest: reserva 24h + `requiere_autenticacion`. Auth: prórroga 10 min, carrito `en_pago` y PaymentIntent. |
| POST | `/api/v1/pagos/webhook` | Firma `Stripe-Signature`, `payment_intent.succeeded` / `payment_intent.payment_failed`. |
| GET | `/api/v1/pagos/{payment_intent_id}` | Polling: `procesando` / `confirmado` / `rechazado` + pedido. |
| GET | `/api/v1/pedidos/{numero}` | Pedido propio con ítems, monto y entrega. |

- La respuesta guest conserva HU-05 (sin `payment_intent_id` ni `client_secret`) y añade
  `requiere_autenticacion: true`.
- El checkout autenticado valida propiedad de la dirección y zona activa antes de contactar a Stripe;
  `retiro` ignora `direccion_id`.
- Clave de idempotencia `pedido-{carrito_id}-{intento}`; número de pedido `BL-<secuencia>`.
- Webhook: transacción corta que convierte reservas en decremento definitivo, crea `Pedido`
  (`Registrado` o `incidencia_stock`), `PedidoItem`, `Pago` y marca el carrito `completado`
  (ítems vaciados). Duplicados idempotentes; firma ausente/inválida → 400.
- `payment_failed`: libera reservas, conserva ítems, carrito vuelve a `activo`, sin pedido ni
  descuento. Eventos `pedido.confirmado` / `despacho.organizar` best-effort.

### Modelos y migración

- Migración `0003_create_pagos_y_entrega.py`: `zonas` (seed `Botica Centro`), `direcciones`,
  `pedidos`, `pedido_items`, `pagos`. Seed adicional en `infra/seed-zonas.sql`.
- `InventarioStock`: `disponible` = stock físico, `reservado` = unidades apartadas. La reserva ya no
  descuenta `disponible`; la confirmación descuenta ambas columnas dentro de la misma TX. Esto
  mantiene la anti-sobreventa y hace observable el decremento definitivo.

### Stripe y seguridad

- Gateway HTTP con `httpx` (sin SDK): PaymentIntent vía `POST /v1/payment_intents` con
  `Idempotency-Key`; verificación de firma HMAC-SHA256 con tolerancia de 5 min.
- Sin clave configurada se usa modo test local: `pi_test_*` y secreto de webhook por defecto
  `whsec_test` (coordinado con TESTER). Con claves reales (`sk_test_*`, `whsec_*`) se usa la API.
- Solo se persisten ids de Stripe y la clave de idempotencia; nunca tarjetas, CVC ni secretos en
  logs. `.env.example` incluye placeholders sin secretos.
- `backend/web.config` ya autoriza `js.stripe.com`, `hooks.stripe.com` y `api.stripe.com` en la CSP;
  no requirió cambios.
- Ajuste necesario en el limitador de auth: 3 req/min por IP **y endpoint** para que el flujo
  registro→activar→login no agote el cupo al crear varios usuarios (HU-01 sigue en 429 en el 4º
  registro).

## 2. Frontend

- `/checkout` (`src/pages/Checkout.tsx`): captura de entrega (retiro/delivery, zonas, direcciones),
  Stripe Elements, botón `Pagar ahora`, `Procesando pago...` con polling y confirmación inline
  `#BL-####` / `S/ x.xx`. Rechazos con los dos mensajes exactos del contrato y carrito intacto.
- `/pedidos/:numero` (`src/pages/Confirmacion.tsx`) y enlace `Continuar al pago` desde `/carrito`.
- Stripe.js se carga desde `https://js.stripe.com/v3/` (CSP autorizada). No hay paquetes npm
  instalados para `@stripe/*`: `vite.config.ts` usa un puente local (`src/stripe-stubs/`) con el
  mismo contrato de importación; así `tsc`, `vite build` y los mocks virtuales de Vitest funcionan
  sin red.

## 3. Verificación

```powershell
cd backend
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python.exe -m pytest tests/test_hu07_pagos_pedidos.py -q
```

- HU-07: **24 passed, 2 skipped** (los 2 skips son NO VERIFICADO del contrato).
- Regresión HU-05: **14 passed, 3 skipped**.
- Regresión HU-01/HU-03/HU-04: **32 passed, 3 skipped**.

```powershell
cd frontend
npm test            # 11 archivos, 41 passed
npm run build       # OK
```

## 4. Rutas tocadas

- `backend/alembic/versions/0003_create_pagos_y_entrega.py`
- `backend/src/modules/pagos/**`, `backend/src/modules/carrito/{inventory,schemas,router}.py`
- `backend/src/core/rate_limit.py`, `backend/src/config.py`, `backend/src/main.py`,
  `backend/.env.example`
- `frontend/src/pages/{Checkout,Confirmacion,Carrito}.tsx`, `frontend/src/services/pagos.ts`,
  `frontend/src/stripe-stubs/**`, `frontend/src/App.tsx`, `frontend/src/vite-env.d.ts`
- `frontend/index.html`, `frontend/vite.config.ts`, `infra/seed-zonas.sql`, `informes/DEV-HU-07.md`

No se tocaron tests ni `contratos/**`.
