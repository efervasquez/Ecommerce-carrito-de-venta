# CONTRATO — HU-09 Gestión de reclamos por producto en mal estado, logística inversa en campo y política de cero reembolsos

**Tipo:** Feature  
**Versión:** v1  
**Estado:** Aprobado (2026-11-26, usuario humano)  
**Origen:** `HUs/HU-09-logistica-inversa-reclamos-y-cambio-fisico.md`

---

## Paquete de contexto

| Fuente | Por qué entra |
|---|---|
| `HUs/HU-09-logistica-inversa-reclamos-y-cambio-fisico.md` | Historia, alcance (RF-04.1 a RF-04.4), criterios de aceptación 1 al 6 y escenarios Gherkin. |
| `TECH-DESIGN.md` §Logística inversa de Reclamos (L122-127) | Exigencia de foto y comprobante; pedido de reposición (total 0.00); `merma_averiada`; máx. 3 intentos adicionales en campo; escalado a supervisión. |
| `TECH-DESIGN.md` §Puntos Abiertos (L136) | **PA-04 (reclamos):** Sub-flujo posterior manual tras `Entregado`, sin estados adicionales en la orden original. |
| `adrs/0003-modelo-datos.md` | Entidad `Reclamo` vinculada a `Pedido` origen; generación de `Pedido` derivado con `tipo='reposicion'`, total 0.00 y reserva de stock; registro de `merma_averiada`. |
| `adrs/0004-contratos-api.md` | Convenciones REST `/api/v1`, esquemas JSON/Multipart, JWT + scopes RBAC. |
| `adrs/0015-lpdp.md` | Protección y almacenamiento seguro de imágenes de evidencias y comprobantes adjuntos. |
| `contratos/CONTRATO-HU-07.md` | Estructura de `Pedido`, `PedidoItem`, numeración `BL-...`, y estados base. |
| `contratos/CONTRATO-HU-08.md` | Buzón de despacho, RBAC (`cliente`, `motorizado`, `admin`), y asignación a motorizado. |

---

## Interfaz observable

- **API HTTP REST:**
  - `POST /api/v1/reclamos` (Multipart: registro de reclamo con evidencias adjuntas).
  - `GET /api/v1/reclamos` (Listado de reclamos; filtrado por cliente dueño o global para admin).
  - `GET /api/v1/reclamos/{id}` (Detalle completo del reclamo, evidencias y estado de reposición).
  - `POST /api/v1/reclamos/{id}/inspeccion-campo` (Inspección física en campo por motorizado: conforme o falla).
  - `POST /api/v1/reclamos/{id}/reembolso` (Intento de reembolso explícitamente bloqueado con HTTP 405 / 400).
- **Frontend Web:**
  - Formulario cliente: `/reclamos/nuevo?pedido_numero=BL-...` (adjuntar foto producto, foto comprobante, motivo).
  - Consulta cliente: `/reclamos` (historial de reclamos del usuario autenticado).
  - Vista motorizado: sección de validación física en campo dentro de `/despacho` (3 checks presenciales y registro de entrega o fallo).
  - Panel admin: `/backoffice/reclamos` (supervisión, filtros de estado, visualización de incidencias escaladas).

---

## Comportamiento

### 1. Autenticación y RBAC

| Caso | Salida esperada | Origen |
|---|---|---|
| Sin sesión (sin JWT) | HTTP 401 en todos los endpoints de `/api/v1/reclamos`. | ADR-0004 |
| Rol `cliente` | Puede registrar reclamos sobre sus propios pedidos `Entregado`, consultar sus propios reclamos. Acceso denegado (HTTP 403) a inspección en campo y backoffice. | **decisión propuesta** |
| Rol `motorizado` | Puede consultar reclamos asignados a su ruta y registrar la inspección física en campo (`POST .../inspeccion-campo`). | RF-04.3; HU-09 crit. 3/4 |
| Rol `admin` | Puede ver todos los reclamos, filtrar por estado, auditar fotos y gestionar reclamos escalados a supervisión. | **decisión propuesta** |

---

### 2. Registro obligatorio del reclamo con evidencias (Cliente)

**Entrada**

```http
POST /api/v1/reclamos
Content-Type: multipart/form-data
Authorization: Bearer <token_cliente>

Campos:
- pedido_numero: "BL-..." (string, requerido)
- producto_id: 123 (int, requerido)
- motivo: "Producto dañado" (string, requerido)
- descripcion: "Frasco quebrado al abrir empaque" (string, opcional)
- foto_producto: <archivo binario JPG/PNG> (requerido)
- foto_comprobante: <archivo binario JPG/PNG/PDF> (requerido)
```

**Casos**

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| **Camino feliz** | Pedido en estado `Entregado` del cliente, producto presente en pedido, foto producto y foto comprobante válidas | HTTP 201; `{ id, pedido_origen_numero, pedido_reposicion_numero, producto_id, estado: "aprobado", intentos_adicionales_realizados: 0, creado_en }`. Dispara creación de pedido de reposición. | HU-09 crit. 1/2; Gherkin esc. 1 |
| **Falta foto producto** | Se omite `foto_producto` | HTTP 422; `{"detail": "La fotografía del producto dañado es obligatoria."}`. | HU-09 crit. 1 |
| **Falta foto comprobante** | Se omite `foto_comprobante` | HTTP 422; `{"detail": "La fotografía o archivo del comprobante de pago es obligatoria."}`. | HU-09 crit. 1 |
| **Formato archivo inválido** | Archivo no es JPG, PNG o PDF | HTTP 422; `{"detail": "Formato de archivo no soportado. Debe ser JPG, PNG o PDF."}`. | ADR-0015 |
| **Pedido no entregado** | Pedido en `Registrado`, `Preparando producto` o `En camino` | HTTP 409; `{"detail": "Solo se pueden registrar reclamos para pedidos con estado Entregado."}`. | HU-09 crit. 6; PA-04 |
| **Pedido no pertenece al cliente** | Pedido de otro usuario o inexistente | HTTP 404; `{"detail": "Pedido no encontrado o no pertenece al usuario autenticado."}`. | ADR-0004; RBAC |
| **Producto no pertenece al pedido** | `producto_id` que no estaba en el pedido | HTTP 422; `{"detail": "El producto indicado no pertenece a los ítems del pedido original."}`. | **decisión propuesta** |
| **Motivo es arrepentimiento** | Motivo indica error de compra, equivocación o arrepentimiento | HTTP 422; `{"detail": "No proceden reclamos por arrepentimiento o error en la compra. Solo aplica para productos dañados o en mal estado."}`. | HU-09 crit. 5; RF-04.2 |

---

### 3. Disparo automático de orden de reposición y stock (Crit. 2)

Al validarse el registro del reclamo:
1. Se crea la entidad `Reclamo` con:
   - `pedido_origen_id` = ID del pedido original.
   - `producto_id` = ID del producto a reponer.
   - `foto_producto_url` = Ruta persistida segura de la foto del producto.
   - `foto_comprobante_url` = Ruta persistida segura del comprobante.
   - `estado` = `"aprobado"`.
   - `intentos_adicionales_realizados` = 0.
2. Se genera de forma automática un nuevo `Pedido` de reposición con:
   - `numero` = Prefijo `BL-REP-...`.
   - `tipo` = `"reposicion"`.
   - `monto` = `0.00` (sin costo para el cliente).
   - `moneda` = `"PEN"`.
   - `usuario_id` = ID del cliente original.
   - `direccion_id` = ID de dirección del pedido original.
   - `zona_id` = ID de zona del pedido original.
   - `metodo_entrega` = `"delivery"`.
   - `estado` = `"Registrado"`.
   - `reclamo_id` = ID del reclamo creado.
3. Se reserva y descuenta 1 unidad de stock de reemplazo del producto.
4. El pedido de reposición queda listo para consolidarse en el buzón de despacho de la zona (W-05, HU-08).

---

### 4. Validación física en campo por el motorizado (Crit. 3 y 4)

**Entrada**

```http
POST /api/v1/reclamos/{id}/inspeccion-campo
Content-Type: application/json
Authorization: Bearer <token_motorizado_o_admin>

Body:
{
  "resultado": "conforme" | "falla",
  "comprobante_verificado": true | false,
  "pertenencia_botica_verificada": true | false,
  "defecto_fisico_verificado": true | false,
  "motivo_falla": "..." (string, opcional si conforme, requerido si falla),
  "observaciones": "..." (string, opcional)
}
```

**Casos**

| Caso | Entrada / Condición | Salida esperada / Efectos | Origen |
|---|---|---|---|
| **Conforme (Éxito)** | `resultado: "conforme"`, los 3 checks en `true` (`comprobante_verificado`, `pertenencia_botica_verificada`, `defecto_fisico_verificado`) | HTTP 200; `{ id, estado: "cerrado_exitoso", mensaje: "Cambio físico completado con éxito." }`. Efectos: Reclamo pasa a `cerrado_exitoso`; pedido de reposición pasa a `Entregado`; producto recogido asentado como `merma_averiada`. | HU-09 crit. 3; Gherkin esc. 1 |
| **Conforme incompleto** | `resultado: "conforme"` pero algún check en `false` | HTTP 422; `{"detail": "Para dar conformidad se deben validar físicamente los 3 requisitos: comprobante original, pertenencia a Botica la Luz y defecto físico."}`. | HU-09 crit. 3 |
| **Falla (Intento 1 o 2 adicional)** | `resultado: "falla"`, `intentos_adicionales_realizados < 2` (se incrementa a 1 o 2) | HTTP 200; `{ id, estado: "reintento_pendiente", intentos_adicionales_realizados: X, intentos_restantes: (3 - X), mensaje: "Intento fallido registrado. Se permite reprogramar nuevo intento de cambio." }`. | HU-09 crit. 4; RF-04.3 |
| **Falla (3er intento adicional alcanzado)** | `resultado: "falla"`, ya tenía 2 intentos adicionales (se incrementa a 3) | HTTP 200; `{ id, estado: "escalado_supervision", intentos_adicionales_realizados: 3, intentos_restantes: 0, mensaje: "Límite de 3 intentos adicionales alcanzado. Reclamo escalado a supervisión." }`. Efectos: Se bloquean nuevos despachos; nuevo producto regresa a stock disponible. | HU-09 crit. 4; Gherkin esc. 2 |
| **Reintento sobre reclamo ya cerrado o escalado** | Reclamo en `cerrado_exitoso` o `escalado_supervision` | HTTP 409; `{"detail": "El reclamo ya no admite inspecciones en campo (estado final alcanzado)."}`. | **decisión propuesta** |
| **Rol no autorizado** | Rol `cliente` intentando inspeccionar | HTTP 403; `{"detail": "Solo el personal de reparto o administración puede registrar inspecciones en campo."}`. | RBAC |

---

### 5. Bloqueo estricto de política de Cero Reembolsos (Crit. 5)

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| Solicitud de reembolso monetario | `POST /api/v1/reclamos/{id}/reembolso` | HTTP 405 Method Not Allowed o HTTP 400 Bad Request; `{"detail": "Política estricta de cero reembolsos: la botica no realiza devoluciones de dinero ni extornos."}`. | HU-09 crit. 5; RF-04.2; PRD §3.2 |
| Parámetro o acción de extorno | Cualquier payload que intente forzar `accion: "reembolso"` | HTTP 422 / 400; `{"detail": "Acción no permitida: política estricta de reposición física sin reembolso monetario."}`. | HU-09 crit. 5 |

---

### 6. Consulta y filtrado de reclamos

**Entradas**

```http
GET /api/v1/reclamos?estado=&pedido_numero=
GET /api/v1/reclamos/{id}
```

| Caso | Salida esperada | Origen |
|---|---|---|
| Listado Cliente | HTTP 200; Devuelve únicamente los reclamos pertenecientes al cliente autenticado. | RBAC |
| Listado Admin | HTTP 200; Devuelve todos los reclamos; permite filtrar por `estado` (`aprobado`, `reintento_pendiente`, `cerrado_exitoso`, `escalado_supervision`) y por `pedido_numero`. | HU-09 crit. 4/6 |
| Reclamo ajeno (cliente) | Si un cliente intenta ver `GET /api/v1/reclamos/{id}` de otro usuario -> HTTP 404. | Seguridad LPDP |

---

## Nombres que no se negocian

| Tipo | Valor exacto |
|---|---|
| Rutas API | `/api/v1/reclamos`, `/api/v1/reclamos/{id}`, `/api/v1/reclamos/{id}/inspeccion-campo`, `/api/v1/reclamos/{id}/reembolso` |
| Estados de Reclamo | `"aprobado"`, `"reintento_pendiente"`, `"cerrado_exitoso"`, `"escalado_supervision"` |
| Tipo de Pedido de Reposición | `"reposicion"` (monto `0.00`) |
| Asiento de descarte | `"merma_averiada"` |
| Campos de inspección física | `comprobante_verificado`, `pertenencia_botica_verificada`, `defecto_fisico_verificado` |
| Límite de intentos adicionales | `3` (máximo 3 intentos adicionales secuenciales en campo) |
| Prefijo pedido de reposición | `BL-REP-` |

---

## Rutas de cada rol

| Rol | Rutas | Origen |
|---|---|---|
| **TESTER** | `backend/tests/test_hu09_reclamos.py`, `frontend/tests/Reclamos.test.tsx` | AGENTS.md / DECISIÓN PROPUESTA |
| **DEV** | `backend/src/modules/reclamos/**`, `backend/alembic/versions/0006_create_reclamos.py`, `backend/src/main.py`, `frontend/src/modules/reclamos/**`, `frontend/src/pages/**`, `frontend/src/App.tsx` | AGENTS.md / DECISIÓN PROPUESTA |

---

## Avisos de contexto

- **Deuda en la zona del cambio (`DEUDA.md`):** Ninguna bloqueante. El módulo de despacho (`backend/src/modules/despacho`) y pagos (`backend/src/modules/pagos`) operan de forma desacoplada y estable.
- **Patrones aplicables (`PATRONES.md`):** 
  - Subida de archivos multipart asíncrona validando tipo MIME y extensión (patrón HU-06).
  - RBAC mediante dependencias de FastAPI (`require_roles("cliente", "admin")`, `require_roles("motorizado", "admin")`) como en HU-08.
  - Creación de entidades vinculadas mediante transacciones atómicas SQLAlchemy (`Reclamo` + `Pedido` reposición + reserva de stock).

---

## Decisiones propuestas (no venían en la tarea)

| # | Decisión | Por qué hace falta | Estado |
|---|---|---|---|
| 1 | Almacenar evidencias (`foto_producto`, `foto_comprobante`) en disco local `./uploads/reclamos/` con UUID único y servir vía URL estática o controlador protegido. | Cumple ADR-0015 (LPDP) y evita almacenar binarios pesados en la tabla MySQL. | Aprobada por usuario humano |
| 2 | Estados exactos del Reclamo: `"aprobado"`, `"reintento_pendiente"`, `"cerrado_exitoso"`, `"escalado_supervision"`. | Provee una máquina de estados clara para los reportes de calidad y el panel administrativo. | Aprobada por usuario humano |
| 3 | Prefijo de número de pedido de reposición: `BL-REP-<numero_origen>`. | Permite trazabilidad inmediata entre el pedido original y su orden de logística inversa. | Aprobada por usuario humano |
| 4 | Al escalar a supervisión (tras agotarse el 3er intento adicional), el producto nuevo no entregado se devuelve automáticamente al stock disponible y el reclamo queda bloqueado para nuevos despachos automáticos. | Cumple ADR-0003 y evita desbalance contable/físico de existencias. | Aprobada por usuario humano |

---

## Fuera del contrato (decide el DEV)

- Esquema exacto de directorios internos dentro de `backend/src/modules/reclamos/`.
- Nombres de funciones internas del servicio (`ReclamoService`, `ReposicionService`, etc.).
- Formato de compresión o thumbnail de las imágenes si se requiere optimización.
- Componentes UI internos y layout en React, siempre que contengan los campos, mensajes y comportamientos observables requeridos.

---

## Preguntas abiertas para el humano

1. ¿Las 4 decisiones propuestas (almacenamiento de evidencias en `./uploads/reclamos/`, máquina de 4 estados, prefijo `BL-REP-`, y liberación de stock al escalar a supervisión) son correctas?
2. ¿Aprobamos este contrato `CONTRATO-HU-09.md` v1 para crear la rama `feat/hu-09-logistica-inversa` y proceder con la invocación de **TESTER** y **DEV** (usando `opencode`, tal como solicitaste)?

---

## Changelog

| Versión | Fecha | Cambio | Motivo | Aprobado por |
|---|---|---|---|---|
| v1 | 2026-11-26 | Versión inicial del contrato HU-09 | Definición de logística inversa, validación en campo y cero reembolsos | Aprobado por usuario humano |
