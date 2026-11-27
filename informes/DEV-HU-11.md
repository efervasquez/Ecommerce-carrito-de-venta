# ENTREGA DEV — HU-11 Reportería y métricas del Backoffice

- **Contrato:** `contratos/CONTRATO-HU-11.md` v1 (aprobado)
- **Rama:** `feat/hu-11-reporteria-backoffice`
- **Tipo:** feature

## 1. Alcance implementado

### Backend

Módulo nuevo `backend/src/modules/reportes/`:

| Archivo | Responsabilidad |
|---|---|
| `auth.py` | RBAC de solo lectura para `admin` y `supervisor` con mensaje 403 contractual. |
| `schemas.py` | DTOs de ventas, balance e inventario crítico. |
| `service.py` | Agregaciones SQL de solo lectura sobre `pedidos`, `pedido_items`, `inventario_stock` y `productos`. |
| `router.py` | Endpoints montados en `/api/v1/backoffice/reportes`. |

Endpoints implementados:

- `GET /api/v1/backoffice/reportes/ventas?fecha_inicio=&fecha_fin=` → `{fecha_inicio, fecha_fin, total_ordenes, unidades_vendidas, monto_total_facturado, moneda: "PEN"}`.
- `GET /api/v1/backoffice/reportes/pedidos-balance` → `{balance: {Registrado, Preparando producto, En camino, Entregado}, total_pedidos}`.
- `GET /api/v1/backoffice/reportes/inventario-critico` → `{stock_bajo, quiebres, mayor_rotacion}`.

Comportamiento:

- Fechas ISO `YYYY-MM-DD` validadas estrictamente; formato inválido → 422 `"El formato de fecha debe ser YYYY-MM-DD."`
- `fecha_fin < fecha_inicio` → 422 `"La fecha de fin no puede ser anterior a la fecha de inicio."`
- Sin fechas → mes en curso (día 1 a hoy).
- Ventas: pedidos `tipo != "reposicion"` creados en el rango (inclusive), con órdenes, suma de unidades de `pedido_items` y suma de `pedidos.monto`.
- Balance: conteo de todos los pedidos agrupado por los 4 estados del ciclo; `total_pedidos` = suma de los 4.
- Inventario: `stock_bajo` con `disponible < 6`, `quiebres` con `disponible == 0`, `mayor_rotacion` por unidades vendidas descendente (excluye reposiciones).
- Cada consulta registra un log estructurado con `reporte`, `usuario_id` y timestamp (middleware de correlación).

### Frontend

- `/backoffice/reportes`: selector de rango de fechas para ventas, tarjetas con totales, tarjetas de balance por estado y tablas de stock bajo, quiebres y mayor rotación.
- Cliente API y tipos co-localizados en `BackofficeReportes.tsx` (única ruta frontend permitida).
- Ruta registrada en `App.tsx`.

## 2. Verificación manual realizada

Pruebas de humo propias (no las del TESTER) contra `test_botica` vía ASGI, con pedidos sembrados en una fecha fija:

- 401 sin token; 403 para `cliente` y `motorizado` con el mensaje exacto.
- 200 con token `admin` y con token `supervisor`.
- Ventas del rango fijo: 3 órdenes, 6 unidades, monto 65.00 PEN; excluye la reposición sembrada.
- Fechas `31-10-2026` y rango invertido → 422 con mensajes exactos; sin fechas → 200 con mes en curso.
- Balance: claves exactas de los 4 estados y valores contrastados contra `GROUP BY estado`; `total_pedidos` consistente.
- Inventario: todo `stock_bajo` estrictamente `< 6`, todo `quiebres` con 0, `mayor_rotacion` ordenada descendente.
- `tsc --noEmit` del frontend y `app.openapi()` sin errores.

## 3. Variables de entorno y migraciones

- **Variables nuevas:** ninguna.
- **Migraciones:** ninguna. La HU es de solo lectura sobre tablas existentes (`0007` vigente en `test_botica`).

## 4. Posible impacto en pruebas existentes

- No modifica esquema ni datos; solo añade endpoints y una ruta frontend.
- Las métricas reflejan la base local completa; pruebas que siembren pedidos deben acotar el rango de fechas o contrastar contra la BD para evitar datos de otras HUs.

## 5. Decisiones / huecos reportados al LEAD

1. **Ventas “confirmadas”:** se consideran todos los pedidos `tipo != "reposicion"` creados en el rango, porque en el sistema un pedido solo se crea tras confirmarse el pago; no se filtra por estado. Confirmar si se debe restringir a `Entregado`.
2. **Balance:** incluye pedidos de reposición y excluye estados fuera de los 4 del contrato (p. ej. `incidencia_stock` o `escalado_supervision`); `total_pedidos` suma solo los 4.
3. **Stock bajo:** usa `disponible` (no `disponible - reservado`); un producto con 0 aparece tanto en `stock_bajo` como en `quiebres`, conforme a las definiciones literales del contrato.
4. **Rotación:** acumulado histórico (sin rango de fechas) y sin reposiciones.
5. **Read-model materializado (ADR-0020):** no se implementaron tablas materializadas ni job de refresco porque el contrato fija agregaciones SQL en vivo sobre las tablas transaccionales y las rutas DEV no incluyen migración ni worker. Queda como deuda arquitectónica si se requiere el aislamiento de carga de ADR-0020.
6. **Roles:** se aceptan `admin` y `supervisor`; cualquier otro rol recibe 403.
