# ENTREGA DEV — HU-09 Logística inversa, reclamos y cero reembolsos

- **Contrato:** `contratos/CONTRATO-HU-09.md` v2 (aprobado)
- **Rama:** `feat/hu-09-logistica-inversa`
- **Tipo:** feature

## 1. Alcance implementado

### Backend

Módulo nuevo `backend/src/modules/reclamos/`:

| Archivo | Responsabilidad |
|---|---|
| `models.py` | `Reclamo` y `MermaAveriada`; enlace con `Pedido` origen y reposición. |
| `schemas.py` | DTO de registro, detalle, listado estándar v2 e inspección. |
| `auth.py` | RBAC con JWT: `cliente`, `motorizado`, `admin`; mensaje contractual de 403 para inspección. |
| `service.py` | Registro con evidencias, reposición, stock, inspección en campo y bloqueo de reembolsos. |
| `router.py` | Endpoints `/api/v1/reclamos` y descarga protegida de evidencias. |

Endpoints implementados:

- `POST /api/v1/reclamos` (multipart) — 201 con pedido de reposición `BL-REP-<origen>`.
- `GET /api/v1/reclamos` — listado con **estructura estándar v2** (7 campos exactos).
- `GET /api/v1/reclamos/{id}` — detalle completo con evidencias y estado de reposición.
- `POST /api/v1/reclamos/{id}/inspeccion-campo` — conforme / falla / escalado.
- `POST /api/v1/reclamos/{id}/reembolso` — 405 política; `accion: "reembolso"` → 400 con mensaje de acción no permitida.
- `GET /api/v1/reclamos/{id}/evidencias/{producto|comprobante}` — controlador protegido (decisión 1).

Comportamiento cubierto:

- Evidencias obligatorias, validación de extensión y MIME, almacenamiento en `./uploads/reclamos/` con UUID.
- Rechazo de motivos de arrepentimiento/error de compra (422).
- Validación de pedido `Entregado`, pertenencia al cliente y producto dentro del pedido.
- Reposición automática: `tipo="reposicion"`, monto `0.00`, `PEN`, `delivery`, estado `Registrado`, `reclamo_id` persistido, ítem con precio 0.
- Descuento transaccional de 1 unidad de stock mediante reserva + deducción.
- Inspección: 3 checks, conforme → `cerrado_exitoso` + reposición `Entregado` + `merma_averiada`; falla → `reintento_pendiente`; 3.er fallo → `escalado_supervision`, devolución de stock y bloqueo de despacho.
- `motivo_falla` obligatorio en falla con el mensaje exacto v2.
- Visibilidad de motorizado heredada **solo** del pedido de reposición asignado (v2).

### Migración

`backend/alembic/versions/0006_create_reclamos.py`

- Crea `reclamos` (FK `pedido_origen_id` CASCADE, `pedido_reposicion_id` SET NULL).
- Crea `merma_averiada` (FK a `reclamos` y `pedidos`).
- Agrega `pedidos.reclamo_id` + índice + FK a `reclamos`.
- `downgrade` verificado (MySQL no permite soltar índices que respaldan FKs; se eliminan con `drop_table`).

### Frontend

- `/reclamos/nuevo?pedido_numero=BL-...`: formulario con **selector de `producto_id`** cargado desde `GET /api/v1/pedidos/{numero}`; foto producto, foto comprobante, motivo y descripción.
- `/reclamos`: historial del cliente con la estructura estándar del listado.
- `/despacho`: sección “Validación física en campo” con los 3 checks, resultado y motivo de falla.
- `/backoffice/reclamos`: filtros por estado y pedido, incidencias escaladas destacadas y detalle con evidencias.

## 2. Verificación manual realizada

Se ejecutaron pruebas de humo propias (no las del TESTER) contra `test_botica` vía ASGI:

- 401 sin token; 403 de cliente en inspección con mensaje exacto.
- 201 de registro; reposición `BL-REP-<origen>`, monto 0, ítem 0, stock descontado.
- 422: sin foto producto, sin comprobante, formato inválido, producto ajeno, arrepentimiento, conforme incompleto, falla sin motivo.
- 404 pedido ajeno; 409 pedido no entregado.
- Falla 1 y 2 → `reintento_pendiente` con intentos/restantes correctos; falla 3 → `escalado_supervision`, stock devuelto; nueva inspección → 409.
- Conforme → `cerrado_exitoso`, reposición `Entregado`, fila en `merma_averiada`, stock no devuelto.
- `GET /reclamos`: exactamente `id`, `pedido_origen_numero`, `pedido_reposicion_numero`, `producto_id`, `estado`, `intentos_adicionales_realizados`, `creado_en`.
- Motorizado: sin asignación de reposición no lista; con asignación lista y ve detalle; la asignación del pedido original no otorga visibilidad.
- Reembolso: sin payload → 405; `accion="reembolso"` → 400.
- `tsc --noEmit` del frontend: sin errores. `app.openapi()`: sin errores.

## 3. Variables de entorno y migraciones

- **Variables nuevas:** ninguna.
- **Migración:** ejecutar `alembic upgrade head` (0005 → 0006).
- En este entorno, `test_botica` quedó migrada a `0006`. La base `ecommerce_botica` de desarrollo **no** fue migrada.

## 4. Posible impacto en pruebas existentes

- El buzón de despacho ahora puede mostrar pedidos `tipo="reposicion"` en estado `Registrado` (comportamiento esperado por HU-09).
- Las pruebas que cuenten pedidos globales pueden requerir limpiar reclamos/reposiciones entre casos, por las nuevas FKs.
- El listado `GET /api/v1/reclamos` devuelve únicamente la estructura v2; cualquier consumidor que esperara campos adicionales del detalle debe usar `GET /api/v1/reclamos/{id}`.

## 5. Decisiones / huecos reportados al LEAD

1. **Stock insuficiente al registrar el reclamo:** el contrato no define el caso. Se devuelve `409 {"detail": "No hay stock suficiente para generar la reposición."}`. Confirmar si se mantiene.
2. **Reclamos duplicados para el mismo pedido/producto:** no se bloquean. Para evitar colisión de `Pedido.numero` (UNIQUE), el segundo reclamo usa `BL-REP-<origen>-<reclamo_id>`. Confirmar si se debe impedir el duplicado.
3. **Inspección por motorizado no asignado:** el contrato v2 vincula la visibilidad a la asignación del pedido de reposición, pero la tabla de casos solo restringe por rol. Se permite inspeccionar a cualquier `motorizado` autenticado. Confirmar si debe exigirse asignación.
4. **Estado del pedido de reposición al escalar:** se usa `escalado_supervision` para bloquear nuevas transiciones de despacho. No es un estado del catálogo base de pedidos; confirmar si se prefiere otro tratamiento.
5. **Endpoint de evidencias:** se agregó `GET /api/v1/reclamos/{id}/evidencias/{tipo}` como “controlador protegido” de la decisión 1, además de la ruta estática permitida por el contrato.
