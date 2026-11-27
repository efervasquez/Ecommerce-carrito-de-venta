# CONTRATO — HU-10 Módulo de contingencia para registro, edición integral de productos y ajuste manual de stock

**Tipo:** Feature  
**Versión:** v1  
**Estado:** Aprobado (2026-11-26, usuario humano)  
**Origen:** `HUs/HU-10-modulo-contingencia-inventario-y-edicion-manual.md`

---

## Paquete de contexto

| Fuente | Por qué entra |
|---|---|
| `HUs/HU-10-modulo-contingencia-inventario-y-edicion-manual.md` | Historia, alcance (RF-05.1, RF-05.2), criterios de aceptación 1 al 5 y escenarios Gherkin. |
| `TECH-DESIGN.md` §Contingencia de stock manual (L128-129) | Backoffice permite alta y edición total de producto (todos los campos del PRD) y actualización directa de existencias. |
| `TECH-DESIGN.md` §Puntos Abiertos (L134) | **PA-02 ("Precios bajos"):** Asignación manual de la etiqueta por el operador/farmacéutico en la ficha del producto (sin regla calculada). |
| `adrs/0003-modelo-datos.md` | Entidades `Producto`, `InventarioStock` y sus atributos comerciales y clínicos completos. |
| `adrs/0004-contratos-api.md` | REST `/api/v1`, esquemas JSON, JWT + RBAC administrativo. |
| `adrs/0011-reserva-stock.md` | Gestión directa de existencias en `inventario_stock` (disponible y reservado). |
| `adrs/0012-erp.md` | Operación en contingencia autónoma y desacoplada del ERP central. |
| `contratos/CONTRATO-HU-03.md` / `CONTRATO-HU-04.md` | Estructura de campos de producto (`PRODUCT_FIELDS` y `DETAIL_FIELDS`). |

---

## Interfaz observable

- **API HTTP REST:**
  - `GET /api/v1/backoffice/productos?q=&limit=&offset=` (Listado y búsqueda de productos con su stock disponible y reservado).
  - `GET /api/v1/backoffice/productos/{id}` (Detalle completo del producto y existencias de inventario).
  - `POST /api/v1/backoffice/productos` (Alta manual de nuevo producto con campos obligatorios y stock inicial).
  - `PUT /api/v1/backoffice/productos/{id}` (Edición integral de atributos comerciales, clínicos y sanitarios).
  - `PATCH /api/v1/backoffice/productos/{id}/stock` (Ajuste manual directo de unidades de stock disponible).
- **Frontend Web:**
  - Panel de inventario: `/backoffice/inventario` (tabla de existencias, buscador por nombre/componente, input rápido para ajuste de stock y botón guardar).
  - Formulario de alta: `/backoffice/inventario/nuevo` (registro con todos los atributos del PRD y stock inicial).
  - Formulario de edición: `/backoffice/inventario/{id}/editar` (edición exhaustiva, selector manual de "Precios bajos", descuentos, textos clínicos).

---

## Comportamiento

### 1. Autenticación y RBAC

| Caso | Salida esperada | Origen |
|---|---|---|
| Sin sesión (sin JWT) | HTTP 401 en todos los endpoints de `/api/v1/backoffice/productos*`. | ADR-0004 |
| Rol `cliente` o `motorizado` | HTTP 403; `{"detail": "Acceso restringido a operadores de inventario y administradores."}`. | AGENTS.md; RBAC |
| Rol `admin` (incluye Farmacéutico / Operador de Stock) | Acceso autorizado a listar, dar de alta, editar y ajustar stock. | HU-10 crit. 5 |

---

### 2. Alta manual de producto (`POST /api/v1/backoffice/productos`)

**Entrada**

```http
POST /api/v1/backoffice/productos
Content-Type: application/json
Authorization: Bearer <token_admin>

Body:
{
  "nombre": "Amoxicilina 500mg",
  "componentes": "Amoxicilina trihidrato",
  "precio_regular": 12.50,
  "moneda": "PEN",
  "stock_disponible": 100,
  "presentacion": "Caja con 20 cápsulas",
  "metodos_entrega": ["delivery", "retiro"],
  "requiere_receta": true,
  "detalle": "Antibiótico bactericida de amplio espectro.",
  "imagen_url": "https://...",
  "descuento_porcentaje": 0.0,
  "precios_bajos": false,
  "contraindicaciones": "Hipersensibilidad a penicilinas.",
  "precauciones_advertencias": "Ajustar dosis en insuficiencia renal.",
  "reacciones_adversas": "Náuseas, diarrea, erupción cutánea."
}
```

**Casos**

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| **Camino feliz** | Todos los campos obligatorios válidos, stock inicial `>= 0`, precio `> 0` | HTTP 201; `{ id, nombre, precio_regular, stock_disponible, ... }`. Crea registro en tabla de productos e inicializa fila en `inventario_stock` con `disponible = stock_disponible`. | HU-10 crit. 2; RF-05.1 |
| **Stock inicial negativo** | `stock_disponible: -5` | HTTP 422; `{"detail": "La cantidad de existencias debe ser un número entero mayor o igual a cero."}`. | HU-10 esc. 2 |
| **Precio regular menor o igual a cero** | `precio_regular: 0` o negativo | HTTP 422; `{"detail": "El precio regular debe ser mayor a cero."}`. | ADR-0003 |
| **Faltan campos obligatorios** | Omisión de `nombre`, `componentes`, `precio_regular`, `presentacion` o `detalle` | HTTP 422; `{"detail": "El campo <nombre_campo> es requerido."}`. | HU-10 crit. 2 |
| **Métodos de entrega inválidos** | Método que no sea `delivery` o `retiro` | HTTP 422; `{"detail": "Los métodos de entrega permitidos son delivery y retiro."}`. | ADR-0003 |

---

### 3. Ajuste manual directo de stock (`PATCH /api/v1/backoffice/productos/{id}/stock`)

**Entrada**

```http
PATCH /api/v1/backoffice/productos/{id}/stock
Content-Type: application/json
Authorization: Bearer <token_admin>

Body:
{
  "stock_disponible": 50,
  "motivo": "Ajuste manual de contingencia por recepción física"
}
```

**Casos**

| Caso | Entrada / Condición | Salida esperada / Efectos | Origen |
|---|---|---|---|
| **Camino feliz** | `stock_disponible: 50` (entero `>= 0`) | HTTP 200; `{ id, producto_id, disponible: 50, reservado: X, actualizado_en }`. Actualiza de inmediato `inventario_stock.disponible = 50`. Registra log de auditoría con `usuario_id` y timestamp. | HU-10 crit. 3; Gherkin esc. 1 |
| **Stock negativo** | `stock_disponible: -10` | HTTP 422; `{"detail": "La cantidad de existencias debe ser un número entero mayor o igual a cero."}`. No altera el stock en BD. | HU-10 esc. 2; crit. 3 |
| **Producto inexistente** | ID no encontrado en catálogo | HTTP 404; `{"detail": "Producto no encontrado."}`. | ADR-0004 |
| **Stock no entero** | `stock_disponible: 12.5` o string | HTTP 422; `{"detail": "La cantidad de existencias debe ser un número entero mayor o igual a cero."}`. | HU-10 esc. 2 |

---

### 4. Edición integral del producto (`PUT /api/v1/backoffice/productos/{id}`)

**Entrada**

```http
PUT /api/v1/backoffice/productos/{id}
Content-Type: application/json
Authorization: Bearer <token_admin>

Body con estructura completa modificable:
{
  "nombre": "Omeprazol 20mg",
  "componentes": "Omeprazol",
  "precio_regular": 18.00,
  "descuento_porcentaje": 15.0,
  "precios_bajos": true,
  "requiere_receta": false,
  "presentacion": "Frasco con 30 cápsulas",
  "metodos_entrega": ["delivery", "retiro"],
  "detalle": "Inhibidor de la bomba de protones.",
  "contraindicaciones": "Hipersensibilidad a omeprazol.",
  "precauciones_advertencias": "Consultar médico en embarazo.",
  "reacciones_adversas": "Cefalea, dolor abdominal.",
  "imagen_url": "https://..."
}
```

**Casos**

| Caso | Entrada / Condición | Salida esperada | Origen |
|---|---|---|---|
| **Camino feliz** | Datos válidos, actualización de precio, oferta (15%) y etiqueta "Precios bajos" activa | HTTP 200; `{ id, nombre, precio_regular: 18.0, descuento_porcentaje: 15.0, precios_bajos: true, ... }`. Refleja los cambios de inmediato en la base de datos local. | HU-10 crit. 4; Gherkin esc. 1 |
| **Porcentaje de descuento inválido** | `descuento_porcentaje: 150` o `< 0` | HTTP 422; `{"detail": "El porcentaje de descuento debe estar entre 0 y 100."}`. | **decisión propuesta** |
| **Precio regular menor o igual a cero** | `precio_regular: -2` | HTTP 422; `{"detail": "El precio regular debe ser mayor a cero."}`. | ADR-0003 |
| **Producto inexistente** | ID no encontrado | HTTP 404; `{"detail": "Producto no encontrado."}`. | ADR-0004 |

---

### 5. Consulta y listado en Backoffice (`GET /api/v1/backoffice/productos`)

**Entrada**

```http
GET /api/v1/backoffice/productos?q=&limit=&offset=
Authorization: Bearer <token_admin>
```

| Caso | Salida esperada | Origen |
|---|---|---|
| Listado exitoso | HTTP 200; `{"items": [{ id, nombre, componentes, precio_regular, descuento_porcentaje, stock_disponible, stock_reservado, precios_bajos, requiere_receta }], "total": N}`. | HU-10 crit. 1/3 |
| Búsqueda por filtro `q` | HTTP 200; Filtra productos cuyo nombre o componentes coincidan con el término buscado. | HU-10 crit. 3 |

---

## Nombres que no se negocian

| Tipo | Valor exacto |
|---|---|
| Rutas API | `/api/v1/backoffice/productos`, `/api/v1/backoffice/productos/{id}`, `/api/v1/backoffice/productos/{id}/stock` |
| Mensaje error stock negativo | `"La cantidad de existencias debe ser un número entero mayor o igual a cero."` |
| Mensaje error precio regular | `"El precio regular debe ser mayor a cero."` |
| Mensaje error descuento | `"El porcentaje de descuento debe estar entre 0 y 100."` |
| Campos de inventario | `stock_disponible`, `stock_reservado` |
| Selector de etiqueta | `precios_bajos` (boolean) |
| Métodos de entrega | `delivery`, `retiro` |

---

## Rutas de cada rol

| Rol | Rutas | Origen |
|---|---|---|
| **TESTER** | `backend/tests/test_hu10_contingencia_stock.py`, `frontend/tests/InventarioContingencia.test.tsx` | AGENTS.md / DECISIÓN PROPUESTA |
| **DEV** | `backend/src/modules/inventario/**`, `backend/alembic/versions/0007_create_productos_contingencia.py`, `backend/src/main.py`, `frontend/src/pages/BackofficeInventario.tsx`, `frontend/src/pages/ProductoForm.tsx`, `frontend/src/App.tsx` | AGENTS.md / DECISIÓN PROPUESTA |

---

## Avisos de contexto

- **Deuda en la zona del cambio (`DEUDA.md`):** Ninguna bloqueante.
- **Patrones aplicables (`PATRONES.md`):**
  - Actualización atómica con SQLAlchemy `update(InventarioStock).where(producto_id == ...).values(disponible = ...)`.
  - Si Meilisearch no está disponible, el módulo de contingencia consulta y actualiza directamente la base de datos MySQL local (ADR-0012).
  - RBAC restringido a perfiles administrativos (`require_roles("admin")`).

---

## Decisiones propuestas (no venían en la tarea)

| # | Decisión | Por qué hace falta | Estado |
|---|---|---|---|
| 1 | Crear tabla local `productos` en MySQL mediante migración `0007_create_productos_contingencia.py` para permitir la persistencia autónoma de altas y ediciones sin depender del seed JSON ni de Meilisearch. | Cumple el criterio 1 y RF-05.1 de operación desacoplada y autónoma en contingencia. | Aprobada por usuario humano |
| 2 | En `PATCH /stock`, devolver tanto el nuevo stock disponible como el reservado actual para visualización del operador. | Da visibilidad al operador de si hay reservas activas en curso. | Aprobada por usuario humano |
| 3 | El formulario de edición permite activar o desactivar la etiqueta `precios_bajos` mediante un toggle/checkbox manual. | Resuelve formalmente PA-02. | Aprobada por usuario humano |

---

## Fuera del contrato (decide el DEV)

- Implementación interna de la sincronización en segundo plano hacia Meilisearch si este vuelve a estar disponible.
- Diseño visual detallado de los formularios en React, siempre que contengan los inputs y validaciones estipulados.

---

## Preguntas abiertas para el humano

1. ¿Las 3 decisiones propuestas (tabla `productos` en MySQL para contingencia total, devolución de disponible/reservado en ajuste, y toggle manual de `precios_bajos`) son correctas?
2. ¿Aprobamos este contrato `CONTRATO-HU-10.md` v1 para crear la rama `feat/hu-10-contingencia-stock` y arrancar el ciclo de construcción de la **HU-10** (para luego continuar con la **HU-11**)?

---

## Changelog

| Versión | Fecha | Cambio | Motivo | Aprobado por |
|---|---|---|---|---|
| v1 | 2026-11-26 | Versión inicial del contrato HU-10 | Módulo de contingencia de inventario y edición manual de productos | Aprobado por usuario humano |
