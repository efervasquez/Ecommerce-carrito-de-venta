# CONTRATO — HU-03 Catálogo y búsqueda difusa

**Tipo:** Feature  
**Versión:** v1  
**Estado:** Aprobado (2026-11-23, usuario humano)  
**Origen:** `HUs/HU-03-busqueda-difusa-y-catalogo-scroll-infinito.md`

---

## Paquete de contexto

| Fuente | Por qué entra |
|---|---|
| `HUs/HU-03-busqueda-difusa-y-catalogo-scroll-infinito.md` | Historia, criterios, escenarios y campos visibles de la tarjeta. |
| `TECH-DESIGN.md` §Criterios de aceptación por flujo | Fuzzy search, scroll infinito, umbral de stock bajo y rendimiento objetivo. |
| `adrs/0005-cqrs-catalogo.md` | Lecturas del catálogo separadas de escrituras y modelo de lectura cacheable. |
| `adrs/0006-busqueda-fuzzy.md` | Meilisearch, tolerancia a typos, filtros y sincronización por eventos. |
| `adrs/0010-estado-frontend.md` | TanStack Query para estado de servidor, paginación incremental y virtualización. |
| `adrs/0019-seguridad-perimetral-iis.md` | Endpoint de búsqueda y límite de 20 solicitudes por segundo/IP. |
| `HUs/HU-05-carrito-compras-persistencia-y-ofertas.md` | Contexto de la integración futura del botón `Agregar al carrito`. |

## Interfaz observable

- API REST de consulta del catálogo.
- Pantalla web del catálogo con búsqueda, scroll incremental y tarjetas.
- Acción observable de agregar un producto al carrito.

## Comportamiento

### Consulta de catálogo y búsqueda difusa

**Entrada propuesta**

```http
GET /api/v1/catalogo/buscar?q=<texto>&cursor=<cursor>&limit=<n>
```

**Casos**

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| Búsqueda con typo | `q=ibuprofno 400` | HTTP 200 con producto `Ibuprofeno 400mg`, componentes `Ibuprofeno` y sus campos de tarjeta. | HU-03 escenario 1; ADR-0006 |
| Búsqueda por componente | Texto coincidente con principio activo | HTTP 200 con productos cuyo nombre comercial o componentes coincidan. | HU-03 criterio 1 |
| Consulta sin texto | `q` vacío u omitido | HTTP 200 con la primera tanda del catálogo y cursor siguiente si existen más productos. | HU-03 criterio 2; **decisión propuesta** |
| Página incremental | `cursor` devuelto por la respuesta anterior | HTTP 200 con la siguiente tanda, sin duplicar productos de la tanda anterior. | HU-03 criterio 2; ADR-0010 |
| Sin resultados | Texto sin coincidencias | HTTP 200 con lista vacía y estado visible de sin resultados. | **decisión propuesta** |
| Límite inválido | `limit` ausente, menor o mayor al rango aprobado | HTTP 422 indicando parámetro inválido. | **decisión propuesta** |
| Rate limit | Más de 20 consultas por segundo desde una IP | HTTP 429. | ADR-0019 |

**Respuesta propuesta**

```json
{
  "items": [
    {
      "id": 1,
      "nombre": "Ibuprofeno 400mg",
      "componentes": "Ibuprofeno",
      "imagen_url": "https://...",
      "precio_regular": 12.00,
      "moneda": "PEN",
      "descuento_porcentaje": 0,
      "stock_disponible": 10,
      "stock_bajo": false,
      "precios_bajos": false,
      "requiere_receta": false
    }
  ],
  "next_cursor": null,
  "has_next": false
}
```

### Tarjeta de producto

Cada tarjeta visible debe mostrar:

| Elemento | Regla | Origen |
|---|---|---|
| Fotografía | Imagen del producto; usar placeholder si no existe. | HU-03 criterio 3; **decisión propuesta** para placeholder |
| Nombre | Nombre comercial. | HU-03 criterio 3 |
| Componentes | Principios activos. | HU-03 criterio 3 |
| Precio | Precio regular en soles. | HU-03 criterio 3 |
| Oferta | Mostrar porcentaje solo si `descuento_porcentaje > 0`. | HU-03 criterio 3 |
| Stock bajo | Mostrar `Últimas unidades disponibles (menos de 6 en stock)` si `stock < 6`. | HU-03 escenario 2 |
| Precios bajos | Mostrar `Precios bajos` si la marca manual está activa. | HU-03 criterio 3 y PA-02 |
| Acción | Botón accesible `Agregar al carrito`. | HU-03 criterio 3 |

### Scroll infinito

- La pantalla carga la primera tanda sin paginación numérica.
- Al aproximarse al final, solicita la siguiente tanda usando `next_cursor`.
- No muestra controles `Página 1, 2, 3`, `Siguiente` ni `Anterior`.
- Mantiene los productos ya cargados y no recarga toda la página.
- Usa carga asíncrona y conserva un estado visible de carga/error.

Origen: HU-03 criterio 2, exclusiones; ADR-0010.

### Agregar al carrito

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| Producto agregable | Clic en `Agregar al carrito` para un producto con stock | Incrementa el contador local/temporal a `1` y mantiene al cliente en el catálogo. No persiste carrito ni reserva stock; esa integración pertenece a HU-05. | HU-03 criterio 4 y escenario 1; decisión humana aprobada |
| Producto con stock bajo | Clic con `stock < 6` | Se permite la acción mientras haya existencias; se conserva la alerta visible. | HU-03 escenario 2 |

La integración persistente del carrito, reservas, límites y sincronización con backend queda fuera de HU-03 y pertenece a HU-05.

## Nombres que no se negocian

| Tipo | Valor exacto |
|---|---|
| Ruta API propuesta | `GET /api/v1/catalogo/buscar` |
| Query | `q` |
| Query | `cursor` |
| Query | `limit` |
| Respuesta | `items`, `next_cursor`, `has_next` |
| Producto | `id`, `nombre`, `componentes`, `imagen_url`, `precio_regular`, `moneda` |
| Producto | `descuento_porcentaje`, `stock_disponible`, `stock_bajo`, `precios_bajos`, `requiere_receta` |
| Texto | `Últimas unidades disponibles (menos de 6 en stock)` |
| Texto | `Precios bajos` |
| Botón | `Agregar al carrito` |

## Rutas de cada rol

| Rol | Rutas | Origen |
|---|---|---|
| TESTER | `backend/tests/**`, `frontend/tests/**`, `frontend/src/**/*.test.tsx`, `frontend/src/**/*.spec.ts` | `AGENTS.md` |
| DEV | `backend/src/**`, `backend/alembic/**`, `backend/requirements*`, `backend/.env.example`, `frontend/src/**` excepto tests, `frontend/package*.json`, `infra/**` | `AGENTS.md` |
| LEAD | `contratos/**`, `informes/**` | `AGENTS.md` / proceso LEAD |

## Avisos de contexto

- HU-03 es P0 y no tiene dependencia previa de catálogo.
- HU-04 y HU-05 dependen de HU-03 según la priorización aprobada.
- `Meilisearch` y una fuente inicial de productos deben estar disponibles para verificar búsquedas reales.
- No existe `DEUDA.md` formal registrado para esta zona.

## Decisiones propuestas (no fijadas por la HU)

| # | Decisión | Por qué hace falta | Estado |
|---|---|---|---|
| 1 | Ruta `GET /api/v1/catalogo/buscar` y esquema de respuesta indicado | La HU no fija nombres de endpoint ni payload. | Aprobada por usuario humano |
| 2 | Cursor opaco con `limit` y campos `next_cursor`/`has_next` | ADR-0010 exige paginación incremental, pero no fija formato. | Aprobada por usuario humano |
| 3 | `q` vacío devuelve la primera tanda del catálogo | Define el estado inicial del catálogo. | Aprobada por usuario humano |
| 4 | Mensaje/estado de sin resultados y error de carga | Se necesita una salida observable para probar estados vacíos y fallos. | Aprobada por usuario humano |
| 5 | Placeholder de imagen cuando no exista `imagen_url` | La HU exige fotografía, pero no define fallback. | Aprobada por usuario humano |
| 6 | HU-03 deja el botón preparado y usa contador local/temporal; HU-05 implementará persistencia y reservas | El criterio 4 se cruza con una HU posterior. | Aprobada por usuario humano |
| 7 | Datos de catálogo para test: seed local y Meilisearch disponible | Se necesitan productos concretos para probar typos, stock y ofertas. | Aprobada por usuario humano |

## Fuera del contrato (decide el DEV)

- Estructura interna de CQRS, repositorios y servicios.
- Modelo de documentos de Meilisearch, salvo que exponga los campos fijados.
- Algoritmo exacto de ranking mientras cumpla tolerancia y resultados del contrato.
- Estilos y composición visual, respetando textos, campos y accesibilidad.
- Estrategia interna de caché, invalidación y sincronización, respetando ADR-0005/0006/0010.

## Preguntas abiertas para el humano

Ninguna. El usuario aprobó las decisiones propuestas 1–7: el botón tendrá contador local/temporal y la integración persistente queda para HU-05.

## Changelog

| Versión | Fecha | Cambio | Motivo | Aprobado por |
|---|---|---|---|---|
| v1 | 2026-11-23 | Versión inicial y aprobación de decisiones observables | Inicio de HU-03 | Usuario humano |
