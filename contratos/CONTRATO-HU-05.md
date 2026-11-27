# CONTRATO — HU-05 Carrito, persistencia, reservas y ofertas

**Tipo:** Feature  
**Versión:** v1  
**Estado:** Aprobado (2026-11-23, usuario humano)  
**Origen:** `HUs/HU-05-carrito-compras-persistencia-y-ofertas.md`

---

## Paquete de contexto

| Fuente | Por qué entra |
|---|---|
| `HUs/HU-05-carrito-compras-persistencia-y-ofertas.md` | Historia, criterios, escenarios y límites anti-abuso. |
| `adrs/0003-modelo-datos.md` | Sesión guest/autenticada, Carrito, CarritoItem, Producto y Stock. |
| `adrs/0011-reserva-stock.md` | Reserva autenticada al agregar, TTL 24h, liberación automática y proveedor local MySQL. |
| `adrs/0016-anti-abuso-carrito-guest.md` | Reserva guest solo en checkout, límites por SKU/productos/IP y rate limits. |
| `adrs/0012-erp.md` | `LocalMySQLInventoryProvider` como fuente de verdad del MVP. |
| `adrs/0010-estado-frontend.md` | TanStack Query para carrito/servidor y Zustand para estado UI. |
| `adrs/0005-cqrs-catalogo.md` | Lectura de productos desde el modelo de catálogo y separación de escrituras. |
| `contratos/CONTRATO-HU-03.md` y `CONTRATO-HU-04.md` | Campos de producto, ofertas, stock y contador temporal que HU-05 reemplaza por persistencia real. |

## Interfaz observable

- API REST de carrito y reserva.
- Cookie/sesión guest o sesión autenticada.
- Pantalla `/carrito` con ofertas, productos regulares, cantidades y totales.
- Tarea/operación observable de liberación de reservas expiradas.

## Comportamiento

### Lectura del carrito

**Entrada propuesta**

```http
GET /api/v1/carrito
```

**Respuesta propuesta**

```json
{
  "items_oferta": [],
  "items_regulares": [],
  "subtotal": 0.00,
  "ahorro_total": 0.00,
  "total": 0.00,
  "reserva_expira_en": null
}
```

**Casos**

| Caso | Salida esperada | Origen |
|---|---|---|
| Carrito con oferta y regular | HTTP 200; ofertas primero, regulares después; subtotales, ahorro y total correctos. | HU-05 criterio 2/3 y escenario 1 |
| Carrito vacío | HTTP 200 con ambas listas vacías y totales cero. | **decisión propuesta** |
| Sesión nueva | HTTP 200 con carrito ligado a la sesión guest/autenticada. | HU-05 criterio 1; ADR-0003 |

### Agregar al carrito

**Entrada propuesta**

```http
POST /api/v1/carrito/items
Content-Type: application/json

{"producto_id":1,"cantidad":1}
```

| Caso | Salida esperada | Origen |
|---|---|---|
| Autenticado, cantidad válida | HTTP 200; persiste item y reserva inmediatamente la cantidad; TTL 24h. | HU-05 criterio 1/5; ADR-0011 |
| Guest, cantidad válida | HTTP 200; persiste item sin reservar stock todavía. | HU-05 escenario 4; ADR-0016 |
| Suma que supera 3 unidades/SKU | HTTP 409 con mensaje de límite; mantiene cantidad previa. | HU-05 criterio 6 y escenario 5 |
| Guest supera 10 productos distintos | HTTP 409 con mensaje de límite; no agrega. | HU-05 criterio 6; ADR-0016 |
| Cantidad supera stock disponible | HTTP 409 con mensaje de stock insuficiente; no agrega ni reserva. | HU-05 criterio 4 |
| Rate limit 1 req/s con burst 5/IP | HTTP 429 con aviso de reintento. | HU-05 criterio 7; ADR-0016 |

### Modificar y eliminar cantidades

**Entradas propuestas**

```http
PATCH /api/v1/carrito/items/{producto_id}
{"cantidad":2}

DELETE /api/v1/carrito/items/{producto_id}
```

| Caso | Salida esperada | Origen |
|---|---|---|
| Cantidad válida | HTTP 200; actualiza item, reserva y totales. | HU-05 criterio 4 |
| Cantidad superior al stock | HTTP 409; conserva cantidad anterior y muestra `Stock máximo disponible alcanzado (N unidades)`. | HU-05 escenario 2 |
| Eliminar item | HTTP 200; elimina item y libera su reserva si existía. | HU-05 criterio 4; ADR-0011 |
| Producto inexistente en carrito | HTTP 404. | **decisión propuesta** |

### Inicio de checkout guest y reserva

**Entrada propuesta**

```http
POST /api/v1/checkout
```

| Caso | Salida esperada | Origen |
|---|---|---|
| Guest con carrito válido | HTTP 200/201; crea reservas de todos los items por 24h y devuelve `reserva_expira_en`. No procesa pago. | HU-05 criterio 5 y escenario 4; ADR-0016 |
| Guest ya tiene checkout/reserva activa por IP | HTTP 409; exige continuar como autenticado o liberar la reserva anterior. | ADR-0016 |
| Más de 3 inicios/min/IP | HTTP 429. | ADR-0016 |
| Reserva parcial imposible | HTTP 409; no deja reservas parciales. | ADR-0012 `reserve_stock_batch` |

La creación de pago, pedido y webhook queda fuera de HU-05 y pertenece a HU-07.

### Liberación de reservas expiradas

| Caso | Salida esperada | Origen |
|---|---|---|
| Reserva con TTL vencido | Libera stock, elimina/purga carrito vencido y deja el producto disponible nuevamente. | HU-05 escenario 3; ADR-0011 |
| Reserva vigente | No libera stock. | ADR-0011 |
| Carrito en checkout/pago | No libera antes de vencer el TTL/prórroga aplicable. | ADR-0011 C-02 |

### Interfaz `/carrito`

- Muestra sección superior `Productos en Oferta`.
- Cada oferta muestra precio original tachado, descuento y precio final.
- Muestra debajo los productos regulares.
- Permite incrementar, reducir y eliminar.
- Recalcula subtotal, ahorro total y total final sin salir de la pantalla.
- Muestra el estado de expiración de la reserva cuando exista.

Textos fijados por la HU: `Productos en Oferta`, `20% DSCTO`,
`Stock máximo disponible alcanzado (N unidades)` y los controles accesibles de cantidad/eliminación.

## Nombres que no se negocian

| Tipo | Valor propuesto |
|---|---|
| GET | `/api/v1/carrito` |
| POST | `/api/v1/carrito/items` |
| PATCH | `/api/v1/carrito/items/{producto_id}` |
| DELETE | `/api/v1/carrito/items/{producto_id}` |
| POST | `/api/v1/checkout` |
| Campos entrada | `producto_id`, `cantidad` |
| Respuesta | `items_oferta`, `items_regulares`, `subtotal`, `ahorro_total`, `total`, `reserva_expira_en` |
| Sección | `Productos en Oferta` |
| Error | `Stock máximo disponible alcanzado (N unidades)` |
| Error | `Límite máximo de 3 unidades por producto` |
| Acción | `Agregar al carrito` |

## Rutas de cada rol

| Rol | Rutas | Origen |
|---|---|---|
| TESTER | `backend/tests/**`, `frontend/tests/**`, `frontend/src/**/*.test.tsx`, `frontend/src/**/*.spec.ts` | `AGENTS.md` |
| DEV | `backend/src/**`, `backend/alembic/**`, `backend/requirements*`, `backend/.env.example`, `frontend/src/**` excepto tests, `frontend/package*.json`, `infra/**` | `AGENTS.md` |
| LEAD | `contratos/**`, `informes/**` | `AGENTS.md` / proceso LEAD |

## Avisos de contexto

- HU-05 reemplaza el contador local/temporal de HU-03/HU-04 por persistencia real.
- El ERP no participa en MVP; la fuente de stock es MySQL mediante `LocalMySQLInventoryProvider`.
- `POST /api/v1/checkout` solo crea reservas en HU-05; el pago pertenece a HU-07.

## Decisiones propuestas

| # | Decisión | Por qué hace falta | Estado |
|---|---|---|---|
| 1 | Rutas y payloads API indicados | La HU no fija nombres exactos de endpoints ni respuestas. | Aprobada por usuario humano |
| 2 | HTTP 409 para límites, stock insuficiente y conflicto de reserva | Se necesita distinguir conflicto de validación 422. | Aprobada por usuario humano |
| 3 | `POST /api/v1/checkout` crea reserva guest, pero no pago/pedido | HU-05 debe cumplir PA-06 sin adelantar HU-07. | Aprobada por usuario humano |
| 4 | Mensajes exactos de límites y stock indicados | La HU fija algunos mensajes, pero no todos. | Aprobada por usuario humano |
| 5 | Carrito vacío responde HTTP 200 con totales cero | Define el estado inicial observable. | Aprobada por usuario humano |

## Fuera del contrato (decide el DEV)

- Estructura interna, transacciones SQL y nombres de repositorios.
- Implementación concreta de sesiones guest y autenticadas, respetando ADR-0003.
- Job scheduler concreto, siempre que libere reservas vencidas.
- Integración de pago, creación de pedido y webhook de Stripe de HU-07.
- Estilos visuales fuera de textos, controles y orden de secciones fijados.

## Preguntas abiertas para el humano

Ninguna. El usuario aprobó las decisiones 1–5 y confirmó que HU-05 solo reserva stock en checkout; pago y pedido quedan para HU-07.

## Changelog

| Versión | Fecha | Cambio | Motivo | Aprobado por |
|---|---|---|---|---|
| v1 | 2026-11-23 | Versión inicial y aprobación de decisiones observables | Inicio de HU-05 | Usuario humano |
