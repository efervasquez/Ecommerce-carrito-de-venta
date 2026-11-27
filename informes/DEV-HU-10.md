# ENTREGA DEV — HU-10 Contingencia de inventario, alta y edición integral de productos

- **Contrato:** `contratos/CONTRATO-HU-10.md` v1 (aprobado)
- **Rama:** `feat/hu-10-contingencia-stock`
- **Tipo:** feature

## 1. Alcance implementado

### Backend

Módulo nuevo `backend/src/modules/inventario/`:

| Archivo | Responsabilidad |
|---|---|
| `models.py` | `Producto` (ficha local completa) e `InventarioAjuste` (auditoría de stock). |
| `schemas.py` | DTOs de alta, edición, detalle, listado y ajuste de stock. |
| `auth.py` | RBAC admin con mensaje contractual 403 para cliente/motorizado. |
| `service.py` | CRUD de productos, validaciones exactas, ajuste de stock y auditoría. |
| `router.py` | Endpoints `/api/v1/backoffice/productos`. |

Endpoints implementados:

- `GET /api/v1/backoffice/productos?q=&limit=&offset=` → `{items, total}` con exactamente `id`, `nombre`, `componentes`, `precio_regular`, `descuento_porcentaje`, `stock_disponible`, `stock_reservado`, `precios_bajos`, `requiere_receta`.
- `GET /api/v1/backoffice/productos/{id}` → ficha completa + existencias.
- `POST /api/v1/backoffice/productos` → 201; crea producto e inicializa `inventario_stock`.
- `PUT /api/v1/backoffice/productos/{id}` → edición integral; no altera stock.
- `PATCH /api/v1/backoffice/productos/{id}/stock` → `{id, producto_id, disponible, reservado, actualizado_en}` y registro en `inventario_ajustes`.

Validaciones con mensajes exactos del contrato:

- Stock no entero o negativo → 422 `"La cantidad de existencias debe ser un número entero mayor o igual a cero."`
- Precio `<= 0` → 422 `"El precio regular debe ser mayor a cero."`
- Descuento fuera de 0..100 → 422 `"El porcentaje de descuento debe estar entre 0 y 100."`
- Métodos distintos de `delivery`/`retiro` → 422 `"Los métodos de entrega permitidos son delivery y retiro."`
- Faltantes obligatorios → 422 `"El campo <nombre_campo> es requerido."` (handler global existente).
- Rol no admin → 403 `"Acceso restringido a operadores de inventario y administradores."`

### Migración

`backend/alembic/versions/0007_create_productos_contingencia.py`

- Crea `productos` con todos los atributos comerciales/clínicos y `metodos_entrega` como JSON.
- Crea `inventario_ajustes` (producto_id, usuario_id, stock anterior/nuevo, motivo, timestamp).
- **Siembra inicial desde `infra/catalogo-seed.json`** (8 productos, IDs 1..8) para que el backoffice opere sobre el catálogo vigente; `metodos_entrega` se normaliza a `delivery`/`retiro`.
- Inicializa `inventario_stock` con `INSERT IGNORE` usando el stock del seed, sin pisar filas existentes.
- `downgrade` elimina `inventario_ajustes` y `productos`.

### Frontend

- `/backoffice/inventario`: tabla de existencias, buscador por nombre/componente, ajuste rápido de stock por fila con botón Guardar, enlaces a alta y edición.
- `/backoffice/inventario/nuevo`: formulario completo con todos los campos del PRD y stock inicial.
- `/backoffice/inventario/{id}/editar`: edición integral, selector manual de "Precios bajos", descuento, métodos de entrega y textos clínicos.
- Rutas registradas en `App.tsx`.

## 2. Verificación manual realizada

Pruebas de humo propias (no las del TESTER) contra `test_botica` vía ASGI:

- 401 sin token; 403 de cliente con mensaje exacto.
- 422: stock `-5`, precio `0`, métodos `["pickup"]`, falta de `nombre`.
- 201: alta con stock 10, `stock_reservado=0`, métodos normalizados.
- `GET` con `q` único → `total=1` y claves exactas del listado.
- `GET` detalle → 200.
- `PATCH` stock 50 → disponible 50, reservado 0; auditoría insertada; BD actualizada.
- `PATCH` `-10`, `12.5`, `"20"` → 422 sin mutar stock; producto inexistente → 404.
- `PUT` precio 18, descuento 15, `precios_bajos=true` → reflejado; descuento 150 y precio -2 → 422; inexistente → 404.
- Migración `0007` upgrade/downgrade/upgrade verificada; seed de 8 productos y stock inicial correcto.
- `tsc --noEmit` del frontend y `app.openapi()` sin errores.

## 3. Variables de entorno y migraciones

- **Variables nuevas:** ninguna.
- **Migración:** `alembic upgrade head` (0006 → 0007).
- En este entorno, `test_botica` quedó en `0007`. La base `ecommerce_botica` de desarrollo no fue migrada.

## 4. Posible impacto en pruebas existentes

- El seed incorpora los 8 productos del catálogo con IDs 1..8; los nuevos productos parten en ID 9.
- `inventario_stock` puede contener filas de esos productos con su stock de seed. El módulo de carrito ya usa esa fila como fuente de disponibilidad, por lo que el stock ajustado se refleja en reservas.
- El catálogo público (HU-03/04) sigue leyendo Meilisearch/seed para nombre y precio; el contrato excluye la sincronización. Solo el stock cambia en `inventario_stock`.
- Pruebas que asuman una tabla `productos` vacía al inicio deben ajustarse o filtrar por nombre único.

## 5. Decisiones / huecos reportados al LEAD

1. **Seed inicial del catálogo en la migración:** el contrato no lo detalla; se decidió sembrar `productos` desde `infra/catalogo-seed.json` para que la búsqueda de productos existentes (Gherkin: "Omeprazol 20mg") funcione. Confirmar si se mantiene.
2. **Métodos de entrega omitidos:** en alta se asumen `["delivery", "retiro"]`; en edición, si se omiten, se conservan los actuales. Confirmar.
3. **Valores opcionales de edición omitidos:** se conservan los valores actuales (no se resetean).
4. **Edición de precio/nombre no se refleja en el catálogo público:** por la exclusión de sincronización con Meilisearch/ERP; solo el stock se refleja vía `inventario_stock`.
5. **Stock solo entero:** `12.0` se rechaza con el mensaje contractual de stock; `12` es válido.
