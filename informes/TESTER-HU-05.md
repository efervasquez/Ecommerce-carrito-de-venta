# Informe de Entrega — TESTER (HU-05)

**Unidad:** HU-05 — Carrito, persistencia, reservas y ofertas (FEATURE)
**Documento base:** `contratos/CONTRATO-HU-05.md` (v1, aprobada 2026-11-23)
**Rama:** `feat/hu-05-carrito-reservas`
**Autor:** Agente TESTER
**Ronda:** 2 — ajustes de arbitraje LEAD (vuelta 1)

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

### Frontend

```text
cd frontend
npm test -- --run tests/Carrito.test.tsx
Test Files  1 passed (1)
Tests       5 passed (5)
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

## 6. Nota de estado del árbol de trabajo (importante para el LEAD)

La corrida verde de backend se ejecutó contra el árbol de trabajo actual, que
contiene **cambios del DEV aún sin commitear** en rutas fuera de propiedad del
TESTER:

- `backend/src/modules/carrito/service.py` (reintentos/ serialización por actor y
  corrección de `subtotal`/`total`: `subtotal = regular * cantidad`,
  `total = subtotal - ahorro_total`).
- `backend/src/modules/carrito/inventory.py` (creación segura de filas de stock).

La prueba `test_carrito_oferta_primero_calcula_ahorro_y_total` (assert
`total == subtotal - ahorro_total`) depende de la corrección de totales del DEV.
El TESTER **no** commitea esos archivos; corresponden al DEV. Si el LEAD juzga
contra `HEAD` (2c2e269) sin esos cambios, esa prueba y el stock pueden fallar.

## 7. Alcance respetado

- Guest no reserva al agregar; autenticado reserva al agregar; checkout guest reserva.
- TTL se verifica solo como contrato, sin inventar una interfaz interna de purga.
- No se verifica pago, pedido, Stripe ni webhook de HU-07.
- TESTER solo modificó `backend/tests/**`, `frontend/tests/**` e `informes/**`;
  no se tocó producción, `package.json`/`package-lock.json` de raíz ni `frontend/dist`.

## 8. Archivos

- `backend/tests/test_hu05_cart_reservations.py`
- `frontend/tests/Carrito.test.tsx`
- `informes/TESTER-HU-05.md`
