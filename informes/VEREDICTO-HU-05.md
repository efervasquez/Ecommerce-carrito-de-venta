# Informe de Veredicto — HU-05 Carrito, persistencia y reservas

**Fecha:** 2026-11-25
**Documento base:** `contratos/CONTRATO-HU-05.md` v1, aprobado por usuario humano
**Tipo:** Feature
**Rama:** `feat/hu-05-carrito-reservas`
**Entregas:**
- TESTER: `4c3447e` (inicial), `fe943d8` (vuelta 1), `1b94a89` (vuelta 2)
- DEV: `2c2e269` (implementación), `a2204af` (vuelta 1), `bb7393a` (vuelta 2)
**Árbitro:** LEAD

## 1. Dictamen

**APROBADO.** Los 3 casos NO VERIFICADO fueron aceptados por el usuario humano (2026-11-25) como fuera de alcance observable.

- Backend HU-05: **14 PASS / 3 SKIPPED (NO VERIFICADO)**.
- Backend regresión HU-03 + HU-04 + HU-05 juntos: **25 PASS / 3 SKIPPED**.
- Frontend HU-05 (`Carrito.test.tsx`): **5/5 PASS**.
- Frontend suite completa: **10/10 archivos, 37/37 tests PASS**.
- Build TypeScript/Vite: **exitoso**.

## 2. Matriz backend (HU-05)

Ejecución: `pytest tests/test_hu05_cart_reservations.py` → `14 passed, 3 skipped`.

| Caso | Prueba | Resultado |
|---|---|---|
| Carrito guest nuevo, vacío, totales cero | `test_carrito_guest_nuevo_retorna_vacio_y_totales_cero` | PASS |
| Guest persiste item en la misma sesión sin reservar | `test_guest_persiste_item_en_la_misma_sesion_sin_reservar` | PASS |
| Oferta primero: ahorro y total | `test_carrito_oferta_primero_calcula_ahorro_y_total` | PASS |
| Autenticado persiste y reserva TTL 24h | `test_autenticado_agregar_persiste_y_reserva_ttl_24h` | PASS |
| Suma > 3 unidades/SKU → 409 conserva item | `test_suma_superior_a_tres_unidades_sku_retorna_409_y_conserva_item` | PASS |
| Cantidad > stock → 409 | `test_cantidad_superior_al_stock_retorna_409` | PASS |
| PATCH cantidad válida actualiza totales | `test_patch_cantidad_valida_actualiza_totales` | PASS |
| PATCH > stock → 409 mensaje máximo | `test_patch_superior_stock_retorna_409_y_mensaje_maximo` | PASS |
| DELETE item → 200 elimina | `test_delete_item_retorna_200_y_elimina` | PASS |
| DELETE producto inexistente → 404 | `test_delete_producto_inexistente_retorna_404` | PASS |
| Guest > 10 productos distintos → 409 | `test_guest_mas_de_diez_productos_distintos_retorna_409` | SKIPPED (NO VERIFICADO) |
| Checkout guest crea reserva sin pago ni pedido | `test_checkout_guest_crea_reserva_sin_pago_ni_pedido` | PASS |
| Checkout guest repetido con reserva activa → 409 | `test_checkout_guest_repetido_con_reserva_activa_retorna_409` | PASS |
| Rate limit agregar por IP → 429 | `test_rate_limit_agregar_por_ip_retorna_429` | PASS |
| Rate limit checkout por IP → 429 | `test_rate_limit_checkout_por_ip_retorna_429` | PASS |
| TTL vencido libera stock y purga carrito | `test_ttl_vencido_libera_stock_y_purga_carrito` | SKIPPED (NO VERIFICADO) |
| Reserva vigente no libera stock | `test_reserva_vigente_no_libera_stock` | SKIPPED (NO VERIFICADO) |

### Casos NO VERIFICADO (aceptados por el usuario humano, 2026-11-25)

1. `test_guest_mas_de_diez_productos_distintos_retorna_409` — el seed observable expone menos de 11 productos distintos; no se puede provocar el límite sin ampliar el seed.
2. `test_ttl_vencido_libera_stock_y_purga_carrito` — el contrato no fija una operación observable para invocar el job de purga ni para adelantar el reloj 24h.
3. `test_reserva_vigente_no_libera_stock` — requiere controlar el reloj y observar el scheduler sin importar código interno.

## 3. Matriz frontend

| Área | Resultado |
|---|---|
| Carrito: ofertas primero, cantidades, totales, expiración, vacío, error | PASS (5/5) |
| Catálogo (HU-03) alineado a contador persistente | PASS (7/7) |
| Detalle de producto (HU-04) alineado a carrito persistente | PASS (6/6) |
| Resto de la suite (HU-01/HU-02, etc.) | PASS |

Ejecución: `npx vitest run` → `Test Files 10 passed (10)`, `Tests 37 passed (37)`.
Build: `npm run build` → TypeScript y Vite correctos.

## 4. Arbitraje

**Vuelta 1.** Se apartó el código en tres puntos y se devolvió al DEV:
- Totales: `subtotal` debía sumar precio original y `total = subtotal - ahorro_total`. Corregido en `a2204af`.
- Checkout guest repetido: devolvía 200 renovando el TTL en vez de 409. Corregido en `a2204af`.
- Deadlock MySQL 1213 en `add_item` concurrente: `get_available_stock` pasó a solo lectura, creación de fila con savepoint ante `IntegrityError`, retry con jitter sobre 1213/1205 y serialización por IP/sesión. Corregido en `a2204af`.
- Ajustes de prueba (stock con seed controlado, reset de inventario, observables UI) en `fe943d8`.

**Vuelta 2.** El cambio de HU-05 a carrito persistente rompió los tests ya aprobados de HU-03/HU-04 (esperaban el contador temporal). El contrato indica explícitamente que HU-05 reemplaza ese contador, por lo que se apartó la prueba: TESTER actualizó `Catalogo.test.tsx` y `DetalleProducto.test.tsx` al observable persistente, enrutando los mocks por URL (`/api/v1/carrito`, `/carrito/items`, `/catalogo`). Adicionalmente se apartó un fragilidad de código menor: `DetalleProducto.tsx` usaba `.concat` sin guardia; DEV la alineó con `Catalogo.tsx` en `bb7393a`.

**Deuda de infraestructura detectada (no bloquea HU-05, no es regresión):** ejecutar `pytest` sin argumentos desde `backend/` no descubre `tests/pytest.ini` ("async def functions are not natively supported"), y la suite backend completa se cuelga. La validación se hizo por módulos (HU-05 aislado y HU-03+04+05 juntos: 25 PASS / 3 SKIPPED). Se recomienda corregir la configuración de pytest en Sprint posterior.

## 5. Propiedad de rutas

- TESTER: `frontend/tests/**` y `informes/TESTER-HU-05.md`. Commits `4c3447e`, `fe943d8`, `1b94a89`.
- DEV: `backend/src/modules/carrito/**`, `backend/alembic/**`, `backend/src/config.py`, `backend/src/core/rate_limit.py`, `backend/src/main.py`, `frontend/src/pages/**`, `frontend/src/services/cart.ts`, `frontend/src/store/useAuthStore.ts`, `frontend/src/App.tsx`, `infra/**`, `informes/DEV-HU-05.md`. Commits `2c2e269`, `a2204af`, `bb7393a`.
- LEAD: `contratos/CONTRATO-HU-05.md` (`0b46008`), aplicación de migración `0002`, veredicto.
- No se tocaron archivos de paquete raíz ni `frontend/dist` en los commits de los agentes.
