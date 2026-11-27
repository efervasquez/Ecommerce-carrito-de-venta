# Informe de Entrega — TESTER (HU-05)

**Unidad:** HU-05 — Carrito, persistencia, reservas y ofertas (FEATURE)
**Documento base:** `contratos/CONTRATO-HU-05.md` (v1, aprobada 2026-11-23)
**Rama:** `feat/hu-05-carrito-reservas`
**Autor:** Agente TESTER
**Ronda:** 3 — ajustes de arbitraje LEAD (vuelta 2: HU-03 y HU-04 migran al contador persistente)

## 1. Cobertura

Pruebas de caja negra para:

- Lectura, agregado, modificación y eliminación del carrito.
- Persistencia guest y autenticada.
- Ofertas primero, regulares, cantidades, ahorro y total.
- Límites por SKU/productos guest y rate limits.
- Reserva autenticada al agregar y guest al checkout.
- Checkout sin pago ni pedido.
- Frontend `/carrito` con ofertas, cantidades, ahorro, total, reserva y errores.

No se prueban pagos, pedidos ni webhooks de HU-07.

## 2. Matriz Backend (`backend/tests/test_hu05_cart_reservations.py`)

| Área | Prueba | Resultado |
|---|---|---|
| Carrito vacío | `test_carrito_guest_nuevo_retorna_vacio_y_totales_cero` | PASS |
| Persistencia guest | `test_guest_persiste_item_en_la_misma_sesion_sin_reservar` | PASS |
| Oferta/regular/totales | `test_carrito_oferta_primero_calcula_ahorro_y_total` | PASS |
| Reserva autenticada TTL | `test_autenticado_agregar_persiste_y_reserva_ttl_24h` | PASS |
| Límite 3 unidades/SKU | `test_suma_superior_a_tres_unidades_sku_retorna_409_y_conserva_item` | PASS |
| Stock insuficiente | `test_cantidad_superior_al_stock_retorna_409` | PASS |
| PATCH cantidad | `test_patch_cantidad_valida_actualiza_totales` | PASS |
| PATCH sobre stock | `test_patch_superior_stock_retorna_409_y_mensaje_maximo` | PASS |
| DELETE item | `test_delete_item_retorna_200_y_elimina` | PASS |
| DELETE inexistente | `test_delete_producto_inexistente_retorna_404` | PASS |
| Guest >10 productos distintos | `test_guest_mas_de_diez_productos_distintos_retorna_409` | SKIP: el seed expone < 11 productos |
| Checkout guest reserva sin pago/pedido | `test_checkout_guest_crea_reserva_sin_pago_ni_pedido` | PASS |
| Checkout repetido | `test_checkout_guest_repetido_con_reserva_activa_retorna_409` | PASS |
| Rate limit agregar | `test_rate_limit_agregar_por_ip_retorna_429` | PASS |
| Rate limit checkout | `test_rate_limit_checkout_por_ip_retorna_429` | PASS |
| TTL y liberación | `test_ttl_vencido_...`, `test_reserva_vigente_...` | SKIP: fuera de contrato observable |

## 3. Matriz Frontend (`frontend/tests/Carrito.test.tsx`)

| Área | Prueba | Resultado |
|---|---|---|
| Ofertas/regulares/totales | `muestra ofertas primero y productos regulares después` | PASS |
| Cantidad/eliminación | `permite cambiar cantidad y eliminar sin abandonar la pantalla` | PASS |
| Expiración de reserva | `muestra estado de expiración de reserva cuando existe` | PASS |
| Carrito vacío | `muestra estado vacío con totales cero` | PASS |
| Error | `muestra error visible si falla la lectura del carrito` | PASS |

## 4. Evidencia de Ejecución (ronda 2)

### Backend

```text
cd backend
.venv\Scripts\python.exe -m pytest tests\test_hu05_cart_reservations.py -q --color=no
14 passed, 3 skipped in 109.86s
```

Requisito de entorno: la BD `test_botica` debe estar migrada a `0002`
(`sesiones`, `carritos`, `carrito_items`, `inventario_stock`).

### Frontend (caja negra HU-05)

```text
cd frontend
npm test -- --run tests/Carrito.test.tsx
Test Files  1 passed (1)
Tests       5 passed (5)
```

### Frontend (suite completa — vuelta 2)

```text
cd frontend
npx vitest run
EXIT=0
Test Files  10 passed (10)
Tests       37 passed (37)
```

## 5. Ajustes de la vuelta 1 (arbitraje LEAD)

**Backend — `test_patch_superior_stock_retorna_409_y_mensaje_maximo`:**
se abandonó la construcción que PATCHeaba por encima del stock de un producto
"grande" (el límite de 3 unidades/SKU corre antes que el stock y ganaba). Ahora,
de forma de caja negra e idempotente: se elige un producto de stock bajo
(`1..4`), un usuario autenticado reserva `stock-1` (deja disponibilidad 1), un
guest agrega 1 y se PATCHea a 2 → 409 con
`"Stock máximo disponible alcanzado (1 unidades)"`. El 2 ≤ 3 no dispara el
límite, y la reserva se libera en `finally` con `DELETE`.

**Backend — reset de inventario por prueba (fixture `reset_shared_inventory`):**
las pruebas reservan stock de forma persistente en la BD compartida, lo que
agotaba productos entre pruebas/corridas y producía `409 "0 unidades"` en
cascada. El fixture autouse (síncrono, vía `pymysql`) borra `inventario_stock`
antes de cada prueba; el servicio reconstruye cada fila de forma lazy
(`disponible = stock del seed`, `reservado = 0`). Se usa `pymysql` síncrono a
propósito para no crear el engine async global en otro event loop (causaba
`Future ... attached to a different loop`).

**Frontend — alineado a los observables reales del DEV:**
`within(article)` para eliminar el producto correcto, `/Reserva expira en/i`,
textos de vacío `No hay productos en oferta.` / `No hay productos regulares.`
y error `No se pudo actualizar el carrito.`.

## 6. Ajustes de la vuelta 2 (arbitraje LEAD — HU-03 y HU-04)

El `CONTRATO-HU-05` establece que HU-05 **reemplaza** el contador temporal de
HU-03/HU-04 por persistencia real (`GET /api/v1/carrito`). No es regresión de
producto, es evolución de spec: se actualizan aserciones, no el comportamiento.

**`tests/Catalogo.test.tsx` (2 fallos → PASS):**
- Helper `mockRoutedFetch` enruta por URL: `/api/v1/carrito` (GET) y
  `/api/v1/carrito/items` (POST) devuelven un `CartResponse` válido;
  `/api/v1/catalogo` devuelve las páginas en secuencia. Así el `useQuery` del
  carrito ya no desplaza los `mockResolvedValueOnce` de la paginación.
- `solicita la siguiente tanda...` filtra las llamadas al catálogo y verifica
  `cursor=cursor-2` y la conservación de la primera página.
- `muestra el contador Carrito: N...` verifica el `Link` nuevo `Carrito: 0` →
  `Carrito: 1` tras agregar, alimentado por el carrito persistente.

**`tests/DetalleProducto.test.tsx` (6 fallos → PASS):**
- `mockDetailRoutedFetch` enruta por URL: `/api/v1/carrito` devuelve un
  `CartResponse` válido (evita `items_oferta === undefined` → `TypeError ... concat`);
  `/api/v1/catalogo/productos/{id}` devuelve el producto; el POST devuelve el
  carrito actualizado.
- Se conservan íntegros los bloques clínicos, navegación, validación de stock y
  botón deshabilitado sin stock.
- La aserción del detalle busca la llamada por URL (no por índice, porque el
  índice 0 es ahora la consulta del carrito).
- `Agregado al carrito temporal` → `Producto agregado al carrito.` +
  `Ver carrito (2)` (contador persistente tras agregar 2 unidades).
- Call-count de la validación de stock: también cuenta la consulta del carrito
  (2 GET) y verifica explícitamente que no se emite el POST de agregado.

**Suite completa:** `npx vitest run` → `Test Files 10 passed (10)`,
`Tests 37 passed (37)`, `EXIT=0`.

**Resolución de la nota de la vuelta 1:** los cambios del DEV ya fueron
commiteados en `a2204af` (totales, checkout repetido, deadlock) y `bb7393a`
(guardia del contador en DetalleProducto). Las corridas verdes actuales se
ejecutan contra esos commits, no contra cambios sin commitear.

## 7. Alcance respetado

- Guest no reserva al agregar; autenticado reserva al agregar; checkout guest reserva.
- TTL se verifica solo como contrato, sin inventar una interfaz interna de purga.
- No se verifica pago, pedido, Stripe ni webhook de HU-07.
- TESTER solo modificó `backend/tests/**`, `frontend/tests/**` e `informes/**`;
  no se tocó producción, `package.json`/`package-lock.json` de raíz ni `frontend/dist`.

## 8. Archivos

- `backend/tests/test_hu05_cart_reservations.py`
- `frontend/tests/Carrito.test.tsx`
- `frontend/tests/Catalogo.test.tsx`
- `frontend/tests/DetalleProducto.test.tsx`
- `informes/TESTER-HU-05.md`
