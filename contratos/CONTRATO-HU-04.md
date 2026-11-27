# CONTRATO — HU-04 Vista de detalle extendida del producto

**Tipo:** Feature  
**Versión:** v1  
**Estado:** Aprobado (2026-11-23, usuario humano)  
**Origen:** `HUs/HU-04-vista-detalle-extendida-producto.md`

---

## Paquete de contexto

| Fuente | Por qué entra |
|---|---|
| `HUs/HU-04-vista-detalle-extendida-producto.md` | Historia, criterios, escenarios y campos clínicos/comerciales/logísticos. |
| `adrs/0003-modelo-datos.md` | Campos observables de `Producto`, incluyendo presentación, detalle, receta, clínica y entrega. |
| `adrs/0005-cqrs-catalogo.md` | Lecturas del catálogo desde el modelo de lectura. |
| `adrs/0010-estado-frontend.md` | TanStack Query para estado de servidor y Zustand para estado de cliente/UI. |
| `contratos/CONTRATO-HU-03.md` | Convenciones del catálogo y producto; HU-03 ya está aprobada. |
| `HUs/HU-05-carrito-compras-persistencia-y-ofertas.md` | Contexto de la futura integración persistente del carrito. |

## Interfaz observable

- Navegación desde una tarjeta del catálogo.
- API REST de lectura del detalle.
- Pantalla web de detalle de producto.
- Control de cantidad y acción visible de agregar al carrito.

## Comportamiento

### Consulta del detalle

**Entrada propuesta**

```http
GET /api/v1/catalogo/productos/{producto_id}
```

**Casos**

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| Producto existente | ID de producto indexado en el catálogo | HTTP 200 con todos los campos del detalle fijados en este contrato. | HU-04 criterio 1 y 2; ADR-0003 |
| Producto inexistente | ID no encontrado | HTTP 404 con error de recurso no encontrado. | **decisión propuesta** |
| ID inválido | ID no numérico o vacío | HTTP 422. | **decisión propuesta** |

**Respuesta propuesta**

```json
{
  "id": 1,
  "nombre": "Azitromicina 500mg",
  "imagen_url": "https://...",
  "componentes": "Azitromicina dihidrato 500mg",
  "precio_regular": 18.50,
  "moneda": "PEN",
  "descuento_porcentaje": 0,
  "requiere_receta": true,
  "detalle": "...",
  "presentacion": "Caja con 3 tabletas recubiertas",
  "metodos_entrega": ["Delivery", "Retiro en botica"],
  "contraindicaciones": "...",
  "precauciones_advertencias": "...",
  "reacciones_adversas": "...",
  "precios_bajos": false,
  "stock_disponible": 10
}
```

### Pantalla de detalle

| Elemento | Regla | Origen |
|---|---|---|
| Ruta frontend propuesta | `/catalogo/productos/{id}` | HU-04 criterio 1; **decisión propuesta** |
| Fotografía | Mostrar imagen principal o placeholder si falta. | HU-04 criterio 2; **decisión propuesta** para fallback |
| Datos comerciales | Nombre, componentes, precio regular y descuento solo si aplica. | HU-04 criterio 2 |
| Receta | Mostrar `Necesita receta para la venta` cuando `requiere_receta=true`; si no, `Producto de venta libre`. | HU-04 criterio 2 y escenarios |
| Detalle/presentación | Mostrar ambos bloques. | HU-04 criterio 2 |
| Entrega | Mostrar las modalidades habilitadas, incluyendo `Delivery` y/o `Retiro en botica`. | HU-04 criterio 2 y escenario 1 |
| Clínica | Mostrar `Contraindicaciones`, `Precauciones/Advertencias` y `Reacciones adversas`. | HU-04 criterio 2 |
| Precios bajos | Mostrar solo cuando la marca manual está activa. | HU-04 criterio 2 y PA-02 |
| Compra | Mostrar selector numérico y botón `Agregar al carrito`. | HU-04 criterio 3 |

### Selector y acción de compra

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| Cantidad válida | Cantidad entera entre 1 y `stock_disponible` | Botón habilitado; click mantiene la ficha y actualiza el contador local/temporal. | HU-04 criterio 3; decisión de HU-03 |
| Cantidad cero, negativa o no entera | Valor inválido | Error visible y botón no ejecuta la acción. | **decisión propuesta** |
| Cantidad mayor al stock | Valor mayor que `stock_disponible` | Error visible; no permite agregar. | HU-04 criterio 3 |
| Producto sin stock | `stock_disponible=0` | Botón deshabilitado; no agrega. | **decisión propuesta** |

La persistencia del carrito, reserva de stock, límites guest y sincronización con backend quedan fuera
de HU-04 y pertenecen a HU-05.

## Nombres que no se negocian

| Tipo | Valor exacto |
|---|---|
| Ruta API propuesta | `GET /api/v1/catalogo/productos/{producto_id}` |
| Ruta frontend propuesta | `/catalogo/productos/{id}` |
| Campo | `id`, `nombre`, `imagen_url`, `componentes` |
| Campo | `precio_regular`, `moneda`, `descuento_porcentaje`, `requiere_receta` |
| Campo | `detalle`, `presentacion`, `metodos_entrega`, `stock_disponible` |
| Campo | `contraindicaciones`, `precauciones_advertencias`, `reacciones_adversas`, `precios_bajos` |
| Texto | `Necesita receta para la venta` |
| Texto | `Producto de venta libre` |
| Sección | `Contraindicaciones` |
| Sección | `Precauciones/Advertencias` |
| Sección | `Reacciones adversas` |
| Etiqueta | `Precios bajos` |
| Botón | `Agregar al carrito` |

## Rutas de cada rol

| Rol | Rutas | Origen |
|---|---|---|
| TESTER | `backend/tests/**`, `frontend/tests/**`, `frontend/src/**/*.test.tsx`, `frontend/src/**/*.spec.ts` | `AGENTS.md` |
| DEV | `backend/src/**`, `backend/alembic/**`, `backend/requirements*`, `backend/.env.example`, `frontend/src/**` excepto tests, `frontend/package*.json`, `infra/**` | `AGENTS.md` |
| LEAD | `contratos/**`, `informes/**` | `AGENTS.md` / proceso LEAD |

## Avisos de contexto

- HU-03 ya está aprobada y proporciona la lista del catálogo.
- HU-04 es P1 y habilita una decisión de compra informada.
- HU-05 implementará posteriormente persistencia, reservas y carrito real.
- No existe `DEUDA.md` formal registrado para esta zona.

## Decisiones propuestas (no fijadas por la HU)

| # | Decisión | Por qué hace falta | Estado |
|---|---|---|---|
| 1 | Ruta API `GET /api/v1/catalogo/productos/{producto_id}` y payload indicado | La HU no fija endpoint ni nombres de campos. | Aprobada por usuario humano |
| 2 | Ruta frontend `/catalogo/productos/{id}` | La HU solo dice página dedicada. | Aprobada por usuario humano |
| 3 | HTTP 404 para producto inexistente y 422 para ID inválido | Se necesitan errores observables. | Aprobada por usuario humano |
| 4 | Placeholder de imagen si falta fotografía | La HU exige mostrar foto, pero no fija fallback. | Aprobada por usuario humano |
| 5 | Contador local/temporal al agregar; persistencia y reservas en HU-05 | Evita adelantar el alcance de HU-05. | Aprobada por usuario humano |
| 6 | Mensajes de validación de cantidad quedan libres mientras se bloquea la acción | La HU fija el bloqueo, no el texto exacto del error. | Aprobada por usuario humano |

## Fuera del contrato (decide el DEV)

- Estructura interna, consultas, repositorios y mecanismo de lectura.
- Modelo de documento de Meilisearch, salvo que exponga los campos fijados.
- Estilos y composición visual, respetando accesibilidad, textos y datos obligatorios.
- Persistencia del carrito, reservas y reglas anti-abuso de HU-05.

## Preguntas abiertas para el humano

Ninguna. El usuario aprobó las decisiones 1–6 y confirmó la acción local/temporal hasta HU-05.

## Changelog

| Versión | Fecha | Cambio | Motivo | Aprobado por |
|---|---|---|---|---|
| v1 | 2026-11-23 | Versión inicial y aprobación de decisiones observables | Inicio de HU-04 | Usuario humano |
