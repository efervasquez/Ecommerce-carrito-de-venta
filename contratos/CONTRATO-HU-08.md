# CONTRATO — HU-08 Buzón de despacho y ciclo de vida de pedidos

**Tipo:** Feature
**Versión:** v2
**Estado:** Aprobado (2026-11-27, usuario humano)
**Origen:** `HUs/HU-08-buzon-despacho-logistico-y-ciclo-vida-pedidos.md`

---

## Paquete de contexto

| Fuente | Por qué entra |
|---|---|
| `HUs/HU-08-buzon-despacho-logistico-y-ciclo-vida-pedidos.md` | Historia, criterios, escenarios y PA-04. |
| `TECH-DESIGN.md` §Buzón de despacho (L116-120) | Consolidación por zona y transiciones `Registrado` → `Preparando producto` → `En camino` → `Entregado`. |
| `adrs/0003-modelo-datos.md` | `Pedido` (estado, zona, dirección, receta) y `Despacho` (agrupación por zona/motorizado). |
| `adrs/0004-contratos-api.md` | REST `/api/v1`, JWT + scopes RBAC por endpoint. |
| `adrs/0007-broker-workers.md` | Evento `despacho.organizar` (best-effort). |
| `contratos/CONTRATO-HU-07.md` | Pedido creado en `Registrado`, con `zona_id`/`direccion_id`/`metodo_entrega`; `incidencia_stock`. |
| `contratos/CONTRATO-HU-06.md` | `auditoria_receta_pendiente` (productos bajo receta). |

## Interfaz observable

- API Backoffice `/api/v1/despacho/...` para buzón, consolidación por zona, asignación y transiciones.
- RBAC: roles `cliente`, `motorizado`, `admin`.
- Pantallas: `/backoffice/despacho` (admin) y `/despacho` (motorizado).

## Comportamiento

### Roles y sesión

| Caso | Salida esperada | Origen |
|---|---|---|
| Sin sesión | HTTP 401 en todos los endpoints de despacho. | ADR-0004 |
| Rol `admin` | Puede ver el buzón, agrupar por zona, asignar lotes y ver historial. | **decisión propuesta** |
| Rol `motorizado` | Puede ver pendientes de su zona, auto-asignarse (FIFO), avanzar estados de sus pedidos y consultar `GET /api/v1/despacho/pedidos` (le devuelve **solo sus pedidos**; el buzón completo es solo `admin`). | **decisión propuesta**; v2 |
| Rol `cliente` | HTTP 403 en endpoints de despacho. | **decisión propuesta** |

- Usuarios `admin` y `motorizado` se crean mediante **seed** con credenciales tomadas de variables de entorno (sin secretos en el repositorio). | **decisión propuesta**

### Buzón y consolidación por zona

**Entradas**

```http
GET /api/v1/despacho/pedidos?estado=&zona_id=
GET /api/v1/despacho/zonas
```

| Caso | Salida esperada | Origen |
|---|---|---|
| Buzón (admin) | HTTP 200; lista de pedidos con `{ numero, estado, zona_id, distrito, metodo_entrega, motorizado_id, monto, creado_en }`. Permite filtrar por `estado` y `zona_id`. | HU-08 crit.1/2; RF-07.1 |
| Consolidación por zona (admin) | HTTP 200; `[{ zona_id, nombre, distrito, pedidos_registrados, pedidos_preparando, pedidos_en_camino, pedidos_entregados }]`. | HU-08 crit.2; RF-07.1 |
| Pedido `incidencia_stock` | Se lista y filtra, pero **no** puede transicionar por las 4 etapas (fuera del flujo). | **decisión propuesta** |

### Asignación a motorizado (admin)

**Entrada**

```http
POST /api/v1/despacho/asignaciones
Body: { zona_id, pedido_numeros: ["BL-..."], motorizado_id }
```

| Caso | Salida esperada | Origen |
|---|---|---|
| Asignación válida | HTTP 200; los pedidos pasan de `Registrado` a `Preparando producto`, quedan con `motorizado_id` y se registra la transición (fecha/hora + usuario). | HU-08 esc.1; crit.3/5; RF-07.2 |
| Pedido inexistente / de otra zona / no `Registrado` | HTTP 409; no asigna parcialmente. | **decisión propuesta** |
| `motorizado_id` inválido o rol incorrecto | HTTP 422/404. | **decisión propuesta** |
| Rol distinto de `admin` | HTTP 403. | **decisión propuesta** |

### Auto-asignación (motorizado, FIFO)

**Entradas**

```http
GET  /api/v1/despacho/pedidos/pendientes?zona_id=
POST /api/v1/despacho/pedidos/{numero}/auto-asignar
```

| Caso | Salida esperada | Origen |
|---|---|---|
| Pendientes de la zona | HTTP 200; pedidos en `Registrado` ordenados por llegada (FIFO). | HU-08 crit.3; RF-07.2 |
| Auto-asignar el más antiguo | HTTP 200; pedido pasa a `Preparando producto` y se asigna al motorizado firmante. | HU-08 crit.3 |
| Auto-asignar uno que no es el más antiguo de la zona | HTTP 409; debe respetar el orden de llegada. | **decisión propuesta** |
| Rol distinto de `motorizado` | HTTP 403. | **decisión propuesta** |

### Ciclo de vida (4 estados obligatorios)

**Entrada**

```http
PATCH /api/v1/despacho/pedidos/{numero}/estado
Body: { estado: "En camino" | "Entregado" }
```

Máquina de estados: `Registrado` → `Preparando producto` → `En camino` → `Entregado`.

| Caso | Salida esperada | Origen |
|---|---|---|
| `Preparando producto` → `En camino` (motorizado asignado) | HTTP 200; registra fecha/hora y usuario responsable. | HU-08 crit.4; RF-07.3 |
| `En camino` → `Entregado` (motorizado asignado) | HTTP 200; registra fecha/hora y usuario responsable. | HU-08 crit.4 |
| Salto/retroceso inválido | HTTP 409; `"Transición de estado inválida: el pedido debe pasar primero por 'Preparando producto' y 'En camino'"`. Mantiene el estado. | HU-08 esc.2; crit.5 |
| Pedido `incidencia_stock` | HTTP 409; fuera del flujo de 4 estados. | **decisión propuesta** |
| Pedido no asignado al motorizado firmante | HTTP 403. | **decisión propuesta** |

### Auditoría de estados

**Entrada**

```http
GET /api/v1/despacho/pedidos/{numero}/historial
```

| Caso | Salida esperada | Origen |
|---|---|---|
| Historial (admin; motorizado de sus pedidos) | HTTP 200; `[{ estado_anterior, estado_nuevo, usuario_id, timestamp }]` en orden cronológico. | HU-08 crit.5; ADR-0003 |
| Pedido inexistente | HTTP 404. | **decisión propuesta** |

### Pantallas

- `/backoffice/despacho` (admin): buzón de pedidos, agrupación por zona/distrito, selección de lote y asignación a motorizado.
- `/despacho` (motorizado): lista de pendientes FIFO de su zona, auto-asignación y botones de avance `En camino` / `Entregado`.
- Los cambios de estado se reflejan en la UI con el estado actual y su historial. | HU-08 crit.1-5

## Nombres que no se negocian

| Tipo | Valor exacto |
|---|---|
| GET | `/api/v1/despacho/pedidos` |
| GET | `/api/v1/despacho/zonas` |
| POST | `/api/v1/despacho/asignaciones` |
| GET | `/api/v1/despacho/pedidos/pendientes` |
| POST | `/api/v1/despacho/pedidos/{numero}/auto-asignar` |
| PATCH | `/api/v1/despacho/pedidos/{numero}/estado` |
| GET | `/api/v1/despacho/pedidos/{numero}/historial` |
| Estados | `Registrado`, `Preparando producto`, `En camino`, `Entregado` |
| Estado de contingencia (fuera de flujo) | `incidencia_stock` |
| Roles | `cliente`, `motorizado`, `admin` |
| Campos asignación | `zona_id`, `pedido_numeros`, `motorizado_id` |
| Campos historial | `estado_anterior`, `estado_nuevo`, `usuario_id`, `timestamp` |
| Mensaje transición inválida | `Transición de estado inválida: el pedido debe pasar primero por 'Preparando producto' y 'En camino'` |
| Rutas frontend | `/backoffice/despacho`, `/despacho` |

## Rutas de cada rol

| Rol | Rutas | Origen |
|---|---|---|
| TESTER | `backend/tests/**`, `frontend/tests/**`, `frontend/src/**/*.test.tsx`, `frontend/src/**/*.spec.ts` | `AGENTS.md` |
| DEV | `backend/src/**`, `backend/alembic/**`, `backend/requirements*`, `backend/pyproject.toml`, `backend/.env.example`, `backend/web.config`, `frontend/src/**` (excepto tests), `frontend/package*.json`, `infra/**` | `AGENTS.md` |
| LEAD/humano | `contratos/**`, `informes/**`, `AGENTS.md`, `docs/**` | `AGENTS.md` |

## Avisos de contexto

- No existe modelo `Despacho` ni historial de estados; se añade migración para `motorizado_id`/`asignado_en` en `Pedido` y tabla `pedido_estado_historial`.
- RBAC: `rol` ya viaja en el JWT (`scopes=[rol]`), pero **no hay dependency de enforcement**; HU-08 debe añadirla (401 sin sesión, 403 por rol).
- HU-07 crea el pedido en `Registrado` con `zona_id`/`direccion_id`/`metodo_entrega`; el buzón se alimenta de esos pedidos.
- `incidencia_stock` queda fuera del flujo de 4 estados (solo listado/filtrado).
- `auditoria_receta_pendiente` (HU-06) no bloquea transiciones de despacho en este contrato; es auditoría farmacéutica.
- Seed de usuarios `admin`/`motorizado` con credenciales por variables de entorno (sin secretos en repositorio); se requiere también al menos una zona activa (ya existe `infra/seed-zonas.sql`).
- Evento `despacho.organizar` (ADR-0007) es best-effort y no debe bloquear la operación.

## Decisiones propuestas (no venían en la tarea)

| # | Decisión | Por qué hace falta | Estado |
|---|---|---|---|
| 1 | Endpoints, campos y mensajes de §Nombres | La HU no fija contratos ni textos. | Aprobada por humano (2026-11-27) |
| 2 | Asignación simple con `motorizado_id` en `Pedido` (sin Despacho observable) | Evita sobre-alcance; cumple RF-07.1-3. Decisión humana 2026-11-27. | Aprobada por humano (2026-11-27) |
| 3 | Roles `cliente`/`motorizado`/`admin` + seed con passwords por env | No hay enforcement ni usuarios de backoffice. Decisión humana. | Aprobada por humano (2026-11-27) |
| 4 | `incidencia_stock` fuera del flujo de 4 estados | No encaja en RF-07.3. Decisión humana. | Aprobada por humano (2026-11-27) |
| 5 | admin asigna (Registrado→Preparando); motorizado avanza (Preparando→En camino→Entregado) y auto-asignación FIFO | Reparte permisos y dispara transiciones. Decisión humana. | Aprobada por humano (2026-11-27) |
| 6 | Auto-asignación solo del pedido más antiguo de la zona (FIFO) | Interpreta "orden de llegada cronológico". | Aprobada por humano (2026-11-27) |
| 7 | Asignación inválida no es parcial (409) | Consistencia del lote. | Aprobada por humano (2026-11-27) |
| 8 | Auditoría con `usuario_id` y timestamp por transición | HU-08 crit.5. | Aprobada por humano (2026-11-27) |

## Fuera del contrato (decide el DEV)

- Estructura interna de tablas, repositorios y de la dependency RBAC.
- Implementación del seed (script/SQL) y su ejecución por entorno.
- Evento `despacho.organizar` y su publicación best-effort.
- Estilos visuales más allá de rutas, textos, controles y flujo fijados.

## Preguntas abiertas para el humano

Ninguna. Decisiones 2–5 aprobadas por el usuario humano (2026-11-27); el resto se aprueba con el contrato.

## Changelog

| Versión | Fecha | Cambio | Motivo | Aprobado por |
|---|---|---|---|---|
| v1 | 2026-11-27 | Versión inicial; asignación simple + 4 estados, roles y seed, incidencia fuera de flujo | Inicio de HU-08 y respuestas del humano | Usuario humano |
| v2 | 2026-11-27 | Aclara que GET /api/v1/despacho/pedidos para motorizado devuelve solo sus pedidos | Desviación aceptada del DEV en arbitraje | Usuario humano |
