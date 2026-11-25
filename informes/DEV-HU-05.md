# Informe de Entrega DEV — HU-05 Carrito, reservas y ofertas

**Fecha:** 2026-11-23  
**Rol:** DEV  
**Documento base:** `contratos/CONTRATO-HU-05.md` (v1, aprobada 2026-11-23)  
**Tipo de tarea:** Feature  
**Rama:** `feat/hu-05-carrito-reservas`

## 1. Qué se construyó

### Backend

- Nuevas entidades persistentes MySQL: `Sesiones`, `Carritos`, `CarritoItems` e
  `InventarioStock`.
- Migración `0002_create_carrito_y_inventario.py`.
- API:
  - `GET /api/v1/carrito`
  - `POST /api/v1/carrito/items`
  - `PATCH /api/v1/carrito/items/{producto_id}`
  - `DELETE /api/v1/carrito/items/{producto_id}`
  - `POST /api/v1/checkout`
- Sesión guest mediante cookie HttpOnly y sesión autenticada mediante JWT.
- `LocalMySQLInventoryProvider` con reservas y liberaciones usando filas bloqueadas y operaciones
  transaccionales.
- Guest: no reserva al agregar; reserva todos los ítems pendientes en checkout.
- Autenticado: reserva al agregar/modificar.
- TTL configurable de 24 horas y job `python -m src.modules.carrito.jobs` para liberar reservas
  expiradas; script operativo `infra/purge-expired-carts.ps1`.
- Límites configurables: 3 unidades/SKU, 10 productos guest, máximo 15 unidades guest reservadas
  por IP, 1 req/s con burst 5 al agregar y 3 checkouts/min/IP.
- No se implementaron pagos, pedidos, ERP ni confirmación de venta de HU-07.

### Frontend

- Nueva pantalla `/carrito` con TanStack Query y datos persistidos del backend.
- Secciones `Productos en Oferta` y productos regulares.
- Cantidades, eliminación, subtotales, ahorro total, total y expiración de reserva.
- Checkout guest visible como reserva, sin iniciar pago.
- HU-03/HU-04 dejaron de usar el contador temporal como fuente de carrito: agregar producto ahora
  llama a `POST /api/v1/carrito/items` y enlaza a `/carrito`.
- Sesión autenticada guarda el access token en `localStorage` para las llamadas persistentes.

## 2. Verificación manual

```powershell
cd backend
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python.exe -m compileall -q src
```

Casos verificados contra MySQL local y fallback de catálogo:

- Carrito guest vacío: HTTP 200 con totales cero.
- Agregar guest: HTTP 200, item persistido sin reservar.
- Checkout guest: HTTP 200, reserva creada con TTL 24h.
- Lectura posterior: muestra la reserva y totales.
- Límite de 3 unidades/SKU: HTTP 409 con `Límite máximo de 3 unidades por producto`.
- Eliminación: HTTP 200 y liberación de la reserva.
- `alembic current`: revisión `0002 (head)`.

Frontend:

```powershell
cd frontend
npm run build
```

Resultado: TypeScript y Vite compilan correctamente.

## 3. Rutas tocadas

- `backend/alembic/versions/0002_create_carrito_y_inventario.py`
- `backend/src/modules/carrito/**`
- `backend/src/core/rate_limit.py`, `backend/src/config.py`, `backend/src/main.py`,
  `backend/.env.example`
- `frontend/src/pages/{Carrito,Catalogo,DetalleProducto,Home}.tsx`
- `frontend/src/services/cart.ts`, `frontend/src/store/useAuthStore.ts`, `frontend/src/App.tsx`
- `infra/purge-expired-carts.ps1`
- `informes/DEV-HU-05.md`

No se tocaron `backend/tests/**`, `frontend/tests/**`, archivos de paquete de la raíz ni se agregó
`frontend/dist` al commit.

## 4. Vuelta 1 — correcciones del arbitraje LEAD

| # | Defecto | Corrección |
|---|---|---|
| 1 | `subtotal` se calculaba sobre el precio ya descontado y `total == subtotal`. | En `CartService._to_response`, `subtotal` ahora suma `precio_regular * cantidad` por ítem; `total = subtotal - ahorro_total` (precio final). |
| 2 | Segundo `POST /api/v1/checkout` de un guest con reserva activa devolvía 200 y renovaba el TTL. | `checkout_guest` detecta reserva vigente en el propio carrito guest (tras purgar expiradas) y responde HTTP 409 sin renovar el TTL. |
| 3 | `add_item` concurrente provocaba deadlock MySQL 1213 por `INSERT` simultáneo en `sesiones.ip_address`. | Se eliminó la escritura implícita de `inventario_stock` en lecturas (`get_available_stock` ya no crea filas), se hizo la creación de fila tolerante a colisiones con savepoint (`IntegrityError`), se agregó reintento con jitter ante `OperationalError` 1213/1205, y se serializan las operaciones por IP (guest) o sesión (autenticado) para evitar el deadlock de origen. |

### Verificación vuelta 1

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_hu05_cart_reservations.py -q
```

Resultado: **14 passed, 3 skipped** (los 3 skips son los casos TTL marcados como no verificables por el TESTER).

- `test_carrito_oferta_primero_calcula_ahorro_y_total` → pasa.
- `test_checkout_guest_repetido_con_reserva_activa_retorna_409` → pasa.
- `test_rate_limit_agregar_por_ip_retorna_429` → pasa.
- Regresión HU-03 + HU-04 en aislamiento: **11 passed**.

Nota operativa: la base `test_botica` tenía reservas acumuladas de corridas previas
(`producto_id=1 disponible=0 reservado=10`) que hacían fallar adds con 409 por stock. Se limpiaron
`carrito_items`, `carritos`, `sesiones` e `inventario_stock` para correr la suite desde estado limpio.
