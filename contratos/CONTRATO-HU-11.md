# CONTRATO — HU-11 Reportería y métricas del Backoffice para administradores y supervisores

**Tipo:** Feature  
**Versión:** v1  
**Estado:** Aprobado (2026-11-26, usuario humano - Gate Humano pre-aprobado)  
**Origen:** `HUs/HU-11-reporteria-y-metricas-del-backoffice.md`

---

## Paquete de contexto

| Fuente | Por qué entra |
|---|---|
| `HUs/HU-11-reporteria-y-metricas-del-backoffice.md` | Historia, alcance (RF-08.1, RF-08.2, RF-08.3), criterios de aceptación 1 al 5 y escenarios Gherkin. |
| `TECH-DESIGN.md` §Puntos Abiertos (L137) | **PA-05 (reportería):** Matriz de reportería formalizada e incorporada al alcance mediante RF-08 (ADR 0020). |
| `adrs/0020-reporteria-backoffice.md` | Decisiones de arquitectura y rendimiento para consultas agregadas del backoffice. |
| `adrs/0005-cqrs-catalogo.md` | Principio CQRS: lecturas agregadas analíticas desacopladas de las transacciones de escritura. |
| `contratos/CONTRATO-HU-07.md` / `CONTRATO-HU-08.md` | Estados del pedido (`Registrado`, `Preparando producto`, `En camino`, `Entregado`), montos, ítems y fechas de creación. |

---

## Interfaz observable

- **API HTTP REST:**
  - `GET /api/v1/backoffice/reportes/ventas?fecha_inicio=&fecha_fin=` (Consolidado de ventas: total órdenes confirmadas, unidades vendidas, monto total facturado).
  - `GET /api/v1/backoffice/reportes/pedidos-balance` (Distribución de órdenes por cada uno de los 4 estados del ciclo de vida).
  - `GET /api/v1/backoffice/reportes/inventario-critico` (Métricas de reabastecimiento: stock bajo `< 6`, quiebres de stock y rotación comercial).
- **Frontend Web:**
  - Panel interactivo: `/backoffice/reportes` (selector de rango de fechas con visualización de totales, tarjetas/gráfico de balance de pedidos por estado, y tabla de inventario crítico).

---

## Comportamiento

### 1. Autenticación y RBAC

| Caso | Salida esperada | Origen |
|---|---|---|
| Sin sesión (sin JWT) | HTTP 401 en todos los endpoints de `/api/v1/backoffice/reportes*`. | ADR-0004 |
| Rol `cliente` o `motorizado` | HTTP 403; `{"detail": "Acceso restringido a administradores y supervisores."}`. | AGENTS.md; RBAC |
| Rol `admin` | Acceso autorizado de solo lectura a los 3 reportes. | HU-11 crit. 1 |

---

### 2. Reporte consolidado de ventas y facturación (`GET /api/v1/backoffice/reportes/ventas`)

**Entrada**

```http
GET /api/v1/backoffice/reportes/ventas?fecha_inicio=2026-10-01&fecha_fin=2026-10-31
Authorization: Bearer <token_admin>
```

**Casos**

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| **Camino feliz** | Rango válido de fechas | HTTP 200; `{"fecha_inicio": "2026-10-01", "fecha_fin": "2026-10-31", "total_ordenes": N, "unidades_vendidas": U, "monto_total_facturado": M, "moneda": "PEN"}`. | HU-11 crit. 2; RF-08.1; Gherkin esc. 1 |
| **Fecha fin anterior a fecha inicio** | `fecha_inicio=2026-10-31&fecha_fin=2026-10-01` | HTTP 422; `{"detail": "La fecha de fin no puede ser anterior a la fecha de inicio."}`. | **decisión propuesta** |
| **Formato de fecha inválido** | Formato no ISO (ej. `31-10-2026`) | HTTP 422; `{"detail": "El formato de fecha debe ser YYYY-MM-DD."}`. | ADR-0004 |
| **Sin parámetros de fecha** | Omitidos | HTTP 200; Por defecto toma el mes en curso (o últimos 30 días). | **decisión propuesta** |

---

### 3. Balance de pedidos por estado (`GET /api/v1/backoffice/reportes/pedidos-balance`)

**Entrada**

```http
GET /api/v1/backoffice/reportes/pedidos-balance
Authorization: Bearer <token_admin>
```

**Casos**

| Caso | Salida esperada | Origen |
|---|---|---|
| Balance general | HTTP 200; `{"balance": {"Registrado": N1, "Preparando producto": N2, "En camino": N3, "Entregado": N4}, "total_pedidos": T}`. | HU-11 crit. 3; RF-08.2 |

---

### 4. Reporte de inventario crítico (`GET /api/v1/backoffice/reportes/inventario-critico`)

**Entrada**

```http
GET /api/v1/backoffice/reportes/inventario-critico
Authorization: Bearer <token_admin>
```

**Casos**

| Caso | Salida esperada | Origen |
|---|---|---|
| Reporte crítico | HTTP 200; `{"stock_bajo": [{ "producto_id": ID, "nombre": "...", "stock_disponible": S }], "quiebres": [{ "producto_id": ID, "nombre": "...", "stock_disponible": 0 }], "mayor_rotacion": [{ "producto_id": ID, "nombre": "...", "unidades_vendidas": U }]}`. Todos los productos en `stock_bajo` tienen estrictamente `stock_disponible < 6`. | HU-11 crit. 4; RF-08.3; Gherkin esc. 2 |

---

## Nombres que no se negocian

| Tipo | Valor exacto |
|---|---|
| Rutas API | `/api/v1/backoffice/reportes/ventas`, `/api/v1/backoffice/reportes/pedidos-balance`, `/api/v1/backoffice/reportes/inventario-critico` |
| Estados evaluados | `"Registrado"`, `"Preparando producto"`, `"En camino"`, `"Entregado"` |
| Umbral de stock bajo | `< 6` (estrictamente menor a 6 unidades) |
| Campos de venta | `total_ordenes`, `unidades_vendidas`, `monto_total_facturado` |

---

## Rutas de cada rol

| Rol | Rutas | Origen |
|---|---|---|
| **TESTER** | `backend/tests/test_hu11_reportes_backoffice.py`, `frontend/tests/ReportesBackoffice.test.tsx` | AGENTS.md / DECISIÓN PROPUESTA |
| **DEV** | `backend/src/modules/reportes/**`, `backend/src/main.py`, `frontend/src/pages/BackofficeReportes.tsx`, `frontend/src/App.tsx` | AGENTS.md / DECISIÓN PROPUESTA |

---

## Avisos de contexto

- **Deuda en la zona del cambio (`DEUDA.md`):** Ninguna bloqueante.
- **Patrones aplicables (`PATRONES.md`):**
  - Consultas de solo lectura usando agregaciones SQL (`func.count`, `func.sum`) sobre tablas `pedidos`, `pedido_items` e `inventario_stock`.
  - Auditoría de accesos al panel mediante logs estructurados con `usuario_id` y timestamp.

---

## Decisiones acordadas

| # | Decisión | Por qué hace falta | Estado |
|---|---|---|---|
| 1 | `fecha_inicio` y `fecha_fin` aceptan formato ISO `YYYY-MM-DD` con validación de orden cronológico. | Estándar de API REST y consistencia de reportes. | Aprobada por usuario humano |
| 2 | El umbral para `stock_bajo` es fijo en existencias `< 6` según RF-08.3 del PRD. | Define claramente el observable de alerta en inventario. | Aprobada por usuario humano |
| 3 | Operación estrictamente de solo lectura sin mutación de estado. | Respeta principio CQRS (ADR-0005). | Aprobada por usuario humano |

---

## Fuera del contrato (decide el DEV)

- Componentes gráficos de visualización (gráficos de barras o tarjetas) en React.
- Índices de optimización en consultas de fechas.

---

## Changelog

| Versión | Fecha | Cambio | Motivo | Aprobado por |
|---|---|---|---|---|
| v1 | 2026-11-26 | Versión inicial del contrato HU-11 | Reportería y métricas del backoffice | Aprobado por usuario humano |
