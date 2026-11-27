# Informe de Entrega — TESTER (HU-10)

**Unidad:** HU-10 — Módulo de contingencia para registro, edición integral de productos y ajuste manual de stock (FEATURE)
**Documento base:** `contratos/CONTRATO-HU-10.md` (v1, aprobado 2026-11-26)
**Rama:** `feat/hu-10-contingencia-stock`
**Autor:** Agente TESTER
**Entrada:** contrato v1 + tipo feature + rutas TESTER asignadas. No se inspeccionó la implementación del DEV.

## 1. Cobertura

Pruebas de caja negra contra la interfaz observable del contrato:

- RBAC y sesión en `/api/v1/backoffice/productos*`: 401 sin JWT, 403 exacto para motorizado y cliente, 200 para admin.
- Alta manual de producto: camino feliz con inicialización de `inventario_stock`, stock negativo, precio no positivo, campos obligatorios faltantes y métodos de entrega inválidos.
- Ajuste manual de stock: `PATCH .../stock` (disponible/reservado/`actualizado_en`), stock negativo sin alterar, stock no entero (float y string) y producto inexistente.
- Edición integral: precio, descuento, `precios_bajos`, datos clínicos; descuento fuera de rango; precio no positivo; producto inexistente.
- Consulta: `{items, total}`, paginación (`limit`/`offset`), búsqueda por nombre y por componentes, detalle con existencias y 404.
- Frontend: `/backoffice/inventario` (tabla, buscador, ajuste rápido por fila), `/backoffice/inventario/nuevo` y `/backoffice/inventario/{id}/editar`.

## 2. Matriz Backend (`backend/tests/test_hu10_contingencia_stock.py`)

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| §1 Sin sesión → 401 (todos los endpoints) | `TestRBAC::test_sin_sesion_retorna_401` (5 parámetros) | NO EJECUTADA (router no montado) |
| §1 Motorizado → 403 exacto | `TestRBAC::test_motorizado_retorna_403` (5 parámetros) | NO EJECUTADA (router no montado) |
| §1 Cliente → 403 exacto | `TestRBAC::test_cliente_retorna_403` | NO EJECUTADA (router no montado) |
| §1 Admin autorizado | `TestRBAC::test_admin_puede_listar` | NO EJECUTADA (404 en sondeo) |
| §2 Alta: camino feliz + stock inicial | `TestAltaProducto::test_camino_feliz_crea_producto_e_inicializa_stock` | NO EJECUTADA (404 en sondeo) |
| §2 Alta: stock negativo → 422 | `TestAltaProducto::test_stock_inicial_negativo_retorna_422` | NO EJECUTADA (router no montado) |
| §2 Alta: precio ≤ 0 → 422 | `TestAltaProducto::test_precio_regular_no_positivo_retorna_422` (2 parámetros) | NO EJECUTADA (router no montado) |
| §2 Alta: faltan obligatorios → 422 | `TestAltaProducto::test_falta_campo_obligatorio_retorna_422` (5 parámetros) | NO EJECUTADA (router no montado) |
| §2 Alta: métodos inválidos → 422 | `TestAltaProducto::test_metodos_de_entrega_invalidos_retornan_422` (2 parámetros) | NO EJECUTADA (router no montado) |
| §3 Ajuste: camino feliz + reservado | `TestAjusteStock::test_camino_feliz_actualiza_disponible_y_devuelve_reservado` | NO EJECUTADA (router no montado) |
| §3 Ajuste: stock negativo → 422 sin alterar | `TestAjusteStock::test_stock_negativo_retorna_422_sin_alterar` | NO EJECUTADA (router no montado) |
| §3 Ajuste: no entero (float/string) → 422 | `TestAjusteStock::test_stock_no_entero_retorna_422` (2 parámetros) | NO EJECUTADA (router no montado) |
| §3 Ajuste: producto inexistente → 404 | `TestAjusteStock::test_producto_inexistente_retorna_404` | NO EJECUTADA (router no montado) |
| §4 Edición: precio + descuento + precios_bajos | `TestEdicionProducto::test_camino_feliz_actualiza_precio_oferta_y_precios_bajos` | NO EJECUTADA (router no montado) |
| §4 Edición: descuento inválido → 422 | `TestEdicionProducto::test_descuento_invalido_retorna_422` (2 parámetros) | NO EJECUTADA (router no montado) |
| §4 Edición: precio ≤ 0 → 422 | `TestEdicionProducto::test_precio_regular_no_positivo_retorna_422` | NO EJECUTADA (router no montado) |
| §4 Edición: producto inexistente → 404 | `TestEdicionProducto::test_producto_inexistente_retorna_404` | NO EJECUTADA (router no montado) |
| §5 Listado `{items,total}` + paginación + campos | `TestConsulta::test_listado_estructura_paginacion_y_total` | NO EJECUTADA (router no montado) |
| §5 Búsqueda por componentes | `TestConsulta::test_busqueda_por_componentes` | NO EJECUTADA (router no montado) |
| §5 Detalle completo con existencias | `TestConsulta::test_detalle_completo_con_existencias` | NO EJECUTADA (router no montado) |
| §5 Producto inexistente → 404 | `TestConsulta::test_producto_inexistente_retorna_404` | NO EJECUTADA (router no montado) |

## 3. Matriz Frontend (`frontend/tests/InventarioContingencia.test.tsx`)

| Pantalla / comportamiento | Prueba | Resultado |
|---|---|---|
| `/backoffice/inventario`: tabla con disponible y reservado | `muestra la tabla de existencias con disponible y reservado` | NO EJECUTADA (pantalla aún no existe) |
| `/backoffice/inventario`: búsqueda por nombre/componente (`?q=`) | `busca por nombre o componente y consulta ?q=` | NO EJECUTADA (pantalla aún no existe) |
| `/backoffice/inventario`: ajuste rápido por fila + `PATCH .../stock` | `ajusta el stock disponible de una fila y lo guarda` | NO EJECUTADA (pantalla aún no existe) |
| `/backoffice/inventario/nuevo`: campos obligatorios + `POST` | `muestra los campos obligatorios y registra el producto` | NO EJECUTADA (pantalla aún no existe) |
| `/backoffice/inventario/{id}/editar`: precio, descuento y Precios bajos + `PUT` | `edita precio, descuento y activa la etiqueta Precios bajos` | NO EJECUTADA (pantalla aún no existe) |

## 4. Evidencia de ejecución

### Backend

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_hu10_contingencia_stock.py --collect-only -q -c backend/tests/pytest.ini
37 tests collected in 0.26s
```

Sondeo de infraestructura (el router de HU-10 aún no está montado en `src/main.py`; el DEV está en
curso):

```text
pytest TestRBAC::test_admin_puede_listar TestAltaProducto::test_camino_feliz...
FAILED (2) — GET/POST /api/v1/backoffice/productos => HTTP 404 Not Found
```

Por eso el resto se marca NO EJECUTADA: no es un rojo de la implementación, el endpoint todavía no
existe. La autenticación de admin por seed y la conexión a MySQL/RabbitMQ sí funcionaron durante el
sondeo.

### Frontend

```text
cd frontend
npx vitest run tests/InventarioContingencia.test.tsx --reporter=basic
Test Files  1 failed (1)
Tests       5 failed (5)
```

Motivo: `src/pages/BackofficeInventario.tsx` y `src/pages/ProductoForm.tsx` todavía no existen en la
rama; los 5 casos fallan en la carga de la pantalla (`Pantalla /backoffice/inventario no implementada`).
Se entregan escritos, listos para la primera corrida contra la implementación.

## 5. Notas de alcance / supuestos

1. **Cuerpo del `PUT`**: se envía exactamente la estructura del contrato §4 (sin `moneda` ni
   `stock_disponible`); el stock se cambia solo por `PATCH .../stock`.
2. **`total` del listado**: se asume que es el total de la consulta filtrada por `q` (lo natural para
   `limit`/`offset`); la prueba usa un token único en nombre y componentes y espera `total = 3`.
3. **Stock no entero**: el contrato exige el mismo mensaje tanto para `12.5` como para un string; se
   asserta el texto exacto, aunque Pydantic devolvería por defecto un `detail` en lista.
4. **Campos de stock en respuestas**: se exigen `stock_disponible` y `stock_reservado` en el listado,
   detalle y respuesta del `PATCH` (§3 y §5).
5. **UI**: los nombres de inputs se asumen `#campo`/`[name=campo]` con los nombres de API del
   contrato; si el DEV usa otros, se arbitrará en el veredicto.
6. No se probó sincronización con Meilisearch (fuera del contrato, decide el DEV).

## 6. Alcance respetado

- TESTER solo modificó `backend/tests/test_hu10_contingencia_stock.py`,
  `frontend/tests/InventarioContingencia.test.tsx` e `informes/TESTER-HU-10.md`.
- No se leyó ni modificó `backend/src/modules/inventario/**`, `backend/src/main.py`,
  `backend/alembic/versions/0007_*` ni las pantallas del DEV.
- No se publicó: sin push ni merge.

## 7. Archivos

- `backend/tests/test_hu10_contingencia_stock.py`
- `frontend/tests/InventarioContingencia.test.tsx`
- `informes/TESTER-HU-10.md`
