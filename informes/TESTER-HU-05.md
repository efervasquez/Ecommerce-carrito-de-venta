# Informe de Entrega — TESTER (HU-05)

**Unidad:** HU-05 — Carrito, persistencia, reservas y ofertas (FEATURE)
**Documento base:** `contratos/CONTRATO-HU-05.md` (v1, aprobada 2026-11-23)
**Rama:** `feat/hu-05-carrito-reservas`
**Autor:** Agente TESTER

## 1. Cobertura

Se escribieron pruebas de caja negra para:

- Lectura, agregado, modificación y eliminación del carrito.
- Persistencia guest y autenticada.
- Ofertas primero, regulares, cantidades, ahorro y total.
- Límites por SKU/productos guest y rate limits.
- Reserva autenticada al agregar y guest al checkout.
- Checkout sin pago ni pedido.
- Frontend `/carrito` con ofertas, cantidades, ahorro, total, reserva y errores.

No se prueban pagos, pedidos ni webhooks de HU-07.

## 2. Matriz Backend

| Área | Pruebas | Resultado |
|---|---|---|
| Carrito vacío | `test_carrito_guest_nuevo_retorna_vacio_y_totales_cero` | ROJO: endpoint 404 |
| Persistencia guest | `test_guest_persiste_item_en_la_misma_sesion_sin_reservar` | ROJO: endpoint 404 |
| Oferta/regular/totales | `test_carrito_oferta_primero_calcula_ahorro_y_total` | ROJO: endpoint 404 |
| Reserva autenticada TTL | `test_autenticado_agregar_persiste_y_reserva_ttl_24h` | ROJO: endpoint 404 |
| Límite 3 unidades/SKU | `test_suma_superior_a_tres_unidades_sku_retorna_409_y_conserva_item` | ROJO: endpoint 404 |
| Stock insuficiente | `test_cantidad_superior_al_stock_retorna_409` | ROJO: endpoint 404 |
| PATCH cantidad | `test_patch_cantidad_valida_actualiza_totales` | ROJO: endpoint 404 |
| PATCH sobre stock | `test_patch_superior_stock_retorna_409_y_mensaje_maximo` | ROJO: endpoint 404 |
| DELETE item | `test_delete_item_retorna_200_y_elimina` | ROJO: endpoint 404 |
| DELETE inexistente | `test_delete_producto_inexistente_retorna_404` | PASS |
| Guest >10 productos distintos | `test_guest_mas_de_diez_productos_distintos_retorna_409` | NO VERIFICADO si el seed no alcanza 11 productos |
| Checkout guest reserva sin pago/pedido | `test_checkout_guest_crea_reserva_sin_pago_ni_pedido` | ROJO: endpoint 404 |
| Checkout repetido | `test_checkout_guest_repetido_con_reserva_activa_retorna_409` | ROJO: endpoint 404 |
| Rate limit agregar | `test_rate_limit_agregar_por_ip_retorna_429` | ROJO: endpoint 404 |
| Rate limit checkout | `test_rate_limit_checkout_por_ip_retorna_429` | ROJO: endpoint 404 |
| TTL y liberación | `test_ttl_vencido_libera_stock_y_purga_carrito`, `test_reserva_vigente_no_libera_stock` | NO VERIFICADO |

## 3. Matriz Frontend

| Área | Pruebas | Resultado |
|---|---|---|
| Ofertas/regulares/totales | `muestra ofertas primero y productos regulares después` | ROJO: `src/pages/Carrito` no resuelto |
| Cantidad/eliminación | `permite cambiar cantidad y eliminar sin abandonar la pantalla` | ROJO: import no resuelto |
| Expiración de reserva | `muestra estado de expiración de reserva cuando existe` | ROJO: import no resuelto |
| Carrito vacío | `muestra estado vacío con totales cero` | ROJO: import no resuelto |
| Error | `muestra error visible si falla la lectura del carrito` | ROJO: import no resuelto |

## 4. Evidencia de Ejecución

### Backend

```text
13 failed, 1 passed, 3 skipped in 24.87s
```

Los endpoints de carrito y checkout aún devuelven `404 Not Found`. El seed de catálogo se usa solo
para preparar productos observables; los casos que requieren 11 productos distintos quedan no
verificables cuando el seed disponible no alcanza esa cantidad.

Los dos casos de TTL se marcan `NO VERIFICADO` porque la spec no fija endpoint para invocar el job,
ni un mecanismo observable para adelantar 24 horas sin importar scheduler/DB interno.

### Frontend

```text
Test Files  1 failed
Tests       no tests recolectados
```

Vitest no resuelve `frontend/src/pages/Carrito` al momento de la corrida.

## 5. Alcance respetado

- Guest no reserva al agregar; autenticado reserva al agregar; checkout guest reserva.
- Se verifica TTL solo como contrato, sin inventar una interfaz interna para ejecutar la purga.
- No se verifica pago, pedido, Stripe ni webhook de HU-07.
- No se modificaron producción, `package.json`/`package-lock.json` de raíz ni `frontend/dist`.

## 6. Archivos

- `backend/tests/test_hu05_cart_reservations.py`
- `frontend/tests/Carrito.test.tsx`
- `informes/TESTER-HU-05.md`
