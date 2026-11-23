# Informe de Entrega — TESTER (HU-04)

**Unidad:** HU-04 — Vista de detalle extendida del producto (FEATURE)
**Documento base:** `contratos/CONTRATO-HU-04.md` (v1, aprobada 2026-11-23)
**Rama:** `feat/hu-04-detalle-producto`
**Autor:** Agente TESTER

## 1. Cobertura

Se escribieron pruebas de caja negra para:

- `GET /api/v1/catalogo/productos/{id}` con payload completo, 404 y 422.
- Ruta `/catalogo/productos/{id}` con detalle comercial, clínico, receta, entrega y precios bajos.
- Selector de cantidad, validación contra stock y producto sin stock.
- `Agregar al carrito` como contador local/temporal, sin persistencia ni reservas de HU-05.

## 2. Matriz Backend

| Caso | Prueba | Resultado |
|---|---|---|
| Producto existente y payload completo | `test_producto_existente_retorna_payload_completo` | BLOQUEADO por seed/Meilisearch |
| Producto inexistente | `test_producto_inexistente_retorna_404` | BLOQUEADO por seed/Meilisearch |
| ID no numérico | `test_id_no_numerico_retorna_422` | PASS |

El payload completo verifica exactamente los 16 campos fijados por el contrato:
`id`, `nombre`, `imagen_url`, `componentes`, `precio_regular`, `moneda`,
`descuento_porcentaje`, `requiere_receta`, `detalle`, `presentacion`, `metodos_entrega`,
`contraindicaciones`, `precauciones_advertencias`, `reacciones_adversas`, `precios_bajos`
y `stock_disponible`.

## 3. Matriz Frontend

| Área | Pruebas | Resultado |
|---|---|---|
| Detalle comercial/clínico/logístico | `consulta el detalle por id y muestra todos los bloques obligatorios` | PASS |
| Producto de venta libre | `muestra producto de venta libre cuando no requiere receta` | PASS |
| Ruta, cantidad y botón | `mantiene la ruta de detalle y muestra cantidad y botón de compra` | PASS |
| Cantidad válida y contador temporal | `cantidad válida conserva la ficha y actualiza el contador local/temporal` | PASS |
| Cantidad mayor al stock | `cantidad mayor al stock muestra error y no ejecuta una segunda petición` | PASS |
| Producto sin stock | `producto sin stock deshabilita Agregar al carrito` | PASS |

## 4. Evidencia de Ejecución

### Backend

```text
1 passed, 2 failed in 8.69s
```

El caso de ID inválido pasa. Los otros dos casos no alcanzan una respuesta HTTP contractual porque
la implementación intenta el fallback local y registra:

- `JSONDecodeError: Illegal trailing comma` en el seed local de detalle.
- `httpx.ConnectTimeout` al consultar Meilisearch.

No se modificó producción para ocultar esos fallos.

### Frontend

```text
Test Files  1 passed
Tests       6 passed
```

## 5. Alcance respetado

- Se verifica solo contador local/temporal.
- No se verifica persistencia de carrito, reservas ni sincronización backend; pertenecen a HU-05.
- No se modificaron archivos de producción, `package.json`/`package-lock.json` raíz ni `frontend/dist`.

## 6. Archivos

- `backend/tests/test_hu04_product_detail.py`
- `frontend/tests/DetalleProducto.test.tsx`
- `informes/TESTER-HU-04.md`
