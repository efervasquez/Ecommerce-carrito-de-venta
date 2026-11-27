# Informe de Entrega — TESTER (HU-09)

**Unidad:** HU-09 — Reclamos por producto en mal estado, logística inversa en campo y política de cero reembolsos (FEATURE)
**Documento base:** `contratos/CONTRATO-HU-09.md` (v1, aprobado 2026-11-26)
**Rama:** `feat/hu-09-logistica-inversa`
**Autor:** Agente TESTER
**Entrada:** contrato v1 + tipo feature + rutas TESTER asignadas. No se inspeccionó la implementación del DEV.

## 1. Cobertura

Pruebas de caja negra contra la interfaz observable del contrato:

- RBAC y sesión en `/api/v1/reclamos*` (401 sin JWT; 403 de cliente en inspección).
- Registro multipart con evidencias obligatorias y validaciones exactas (fotos, formato, estado del pedido, pertenencia del pedido/producto, arrepentimiento).
- Creación automática del pedido de reposición `BL-REP-...`, monto `0.00`, `PEN`, `delivery`, `Registrado` y compromiso de 1 unidad de stock.
- Inspección física en campo: conformidad (3 checks), conformidad incompleta, fallas secuenciales 1–3, escalado a supervisión, bloqueo de inspecciones en estado final y liberación de stock al escalar.
- Bloqueo de reembolso (405/400) y de acción forzada `accion:"reembolso"` (422/400).
- Consulta: cliente solo ve sus reclamos; admin ve todos y filtra por `estado` y `pedido_numero`; reclamo ajeno → 404.
- Frontend: formulario `/reclamos/nuevo?pedido_numero=...`, historial `/reclamos` y panel admin `/backoffice/reclamos`.

## 2. Matriz Backend (`backend/tests/test_hu09_reclamos.py`)

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| §1 Sin sesión → 401 (todos los endpoints) | `TestRBAC::test_sin_sesion_retorna_401` (5 parámetros) | **PASS (5)** |
| §1 Cliente no inspecciona → 403 | `TestRBAC::test_cliente_no_puede_registrar_inspeccion_en_campo` | NO EJECUTADA (broker) |
| §2 Camino feliz → 201 + reposición + stock | `TestRegistro::test_camino_feliz_crea_reclamo_y_pedido_de_reposicion` | NO EJECUTADA (broker) |
| §2 Falta foto producto → 422 | `TestRegistro::test_falta_foto_producto_retorna_422` | NO EJECUTADA (broker) |
| §2 Falta foto comprobante → 422 | `TestRegistro::test_falta_foto_comprobante_retorna_422` | NO EJECUTADA (broker) |
| §2 Formato inválido → 422 | `TestRegistro::test_formato_de_archivo_invalido_retorna_422` (2 parámetros) | NO EJECUTADA (broker) |
| §2 Pedido no entregado → 409 | `TestRegistro::test_pedido_no_entregado_retorna_409` | NO EJECUTADA (broker) |
| §2 Pedido ajeno → 404 | `TestRegistro::test_pedido_de_otro_cliente_retorna_404` | NO EJECUTADA (broker) |
| §2 Pedido inexistente → 404 | `TestRegistro::test_pedido_inexistente_retorna_404` | NO EJECUTADA (broker) |
| §2 Producto ajeno al pedido → 422 | `TestRegistro::test_producto_que_no_pertenece_al_pedido_retorna_422` | NO EJECUTADA (broker) |
| §2 Motivo arrepentimiento → 422 | `TestRegistro::test_motivo_de_arrepentimiento_retorna_422` (3 parámetros) | NO EJECUTADA (broker) |
| §4 Conforme + 3 checks → `cerrado_exitoso` + reposición `Entregado` | `TestInspeccionCampo::test_conforme_completa_cambio_y_entrega_reposicion` | NO EJECUTADA (broker) |
| §4 Conforme incompleto → 422 | `TestInspeccionCampo::test_conforme_con_check_en_false_retorna_422` (3 parámetros) | NO EJECUTADA (broker) |
| §4 Falla 1/2/3 → reintento y escalado + stock liberado + 409 posterior | `TestInspeccionCampo::test_fallas_secuenciales_escalan_al_tercer_intento` | NO EJECUTADA (broker) |
| §4 Reintento sobre cerrado → 409 | `TestInspeccionCampo::test_reintento_sobre_reclamo_cerrado_retorna_409` | NO EJECUTADA (broker) |
| §5 Reembolso bloqueado → 405/400 | `TestCeroReembolsos::test_solicitud_de_reembolso_esta_bloqueada` | NO EJECUTADA (broker) |
| §5 `accion:"reembolso"` → 422/400 | `TestCeroReembolsos::test_payload_que_fuerza_accion_reembolso_retorna_400_o_422` | NO EJECUTADA (broker) |
| §6 Listado cliente solo propio | `TestConsulta::test_cliente_solo_ve_sus_propios_reclamos` | NO EJECUTADA (broker) |
| §6 Listado admin + filtros | `TestConsulta::test_admin_lista_todos_y_filtra_por_estado_y_pedido` | NO EJECUTADA (broker) |
| §6 Reclamo ajeno → 404 | `TestConsulta::test_reclamo_ajeno_retorna_404` | NO EJECUTADA (broker) |
| §3 `merma_averiada` | `TestNoVerificado::test_merma_averiada_asentada` | SKIP (sin interfaz observable) |
| §4 Bloqueo de nuevos despachos | `TestNoVerificado::test_despachos_bloqueados_tras_escalar` | SKIP (sin código/mensaje pactado) |

## 3. Matriz Frontend (`frontend/tests/Reclamos.test.tsx`)

| Pantalla / comportamiento | Prueba | Resultado |
|---|---|---|
| `/reclamos/nuevo`: precarga `pedido_numero`, motivo y 2 evidencias | `precarga el pedido y exige motivo y las dos evidencias` | PASS |
| `/reclamos/nuevo`: POST multipart con pedido, motivo y ambas fotos | `envía el reclamo por multipart con pedido, motivo y las dos evidencias` | PASS |
| `/reclamos`: historial del cliente con estados | `muestra los reclamos del cliente con su estado` | PASS |
| `/backoffice/reclamos`: todos los reclamos + incidencias escaladas | `muestra todos los reclamos y las incidencias escaladas` | PASS |
| `/backoffice/reclamos`: filtro por `estado` | `filtra por estado escalado_supervision` | PASS |

## 4. Evidencia de ejecución

### Backend

```text
cd <raiz>
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_hu09_reclamos.py --collect-only -q -c backend/tests/pytest.ini
31 tests collected in 0.24s

backend\.venv\Scripts\python.exe -m pytest "backend/tests/test_hu09_reclamos.py::TestRBAC::test_sin_sesion_retorna_401" -q -c backend/tests/pytest.ini
5 passed in 3.30s
```

El resto de la suite quedó **NO EJECUTADA**: el broker RabbitMQ no está disponible en este entorno
(`127.0.0.1:5672` cerrado y sin servicio/Erlang instalado), y el registro/activación de clientes de
HU-01 depende de la cola `email.auth`. No es un rojo de la implementación: no se pudo correr.

Nota de entorno: `python-multipart>=0.0.9` figuraba en `backend/requirements.txt` pero no estaba
instalado en `backend/.venv`; sin él la app ni siquiera importaba (`RuntimeError: Form data requires
"python-multipart"`). Se instaló en el venv local para poder recolectar y ejecutar las pruebas RBAC.

### Frontend

```text
cd frontend
npx vitest run tests/Reclamos.test.tsx --reporter=basic
Test Files  1 passed (1)
Tests       5 passed (5)
```

Se ajustó solo el harness de prueba mientras se ejecutaba contra la UI en curso del DEV:
el mock de `fetch` ahora expone `text()` (el cliente HTTP de la pantalla lo usa) y el filtro del
backoffice se aplica con el botón `Filtrar` del formulario (el componente no filtra al cambiar el
`select`). Ningún ajuste cambió una expectativa del contrato.

## 5. NO VERIFICADO

1. **`merma_averiada`**: el contrato exige asentar el producto recogido, pero no define endpoint ni
   campo observable. No se fuerza por dentro (regla del playbook). Pendiente de arbitraje del LEAD.
2. **Bloqueo de nuevos despachos tras escalar**: no hay código HTTP ni mensaje pactado. El efecto
   verificable (devolución de la unidad al stock) sí se cubre en
   `test_fallas_secuenciales_escalan_al_tercer_intento`.
3. **Inspección física en la UI `/despacho` (3 checks)**: el contrato la menciona, pero no define
   cómo la pantalla obtiene el reclamo asignado ni nombres de campos; fuera de esta prueba de caja
   negra. Reportado al LEAD.
4. **`tipo="reposicion"`**: el detalle de pedido de HU-07 no expone `tipo` en su contrato. Se
   verifica el prefijo `BL-REP-`, `monto 0.00`, `PEN`, `delivery`, `Registrado` y el ítem; si la
   respuesta incluye `tipo`, se asserta `"reposicion"` (assert condicional).

## 6. Huecos de la spec reportados al LEAD (no decididos por TESTER)

1. `producto_id` es requerido por `POST /api/v1/reclamos`, pero el formulario del contrato solo
   menciona foto de producto, foto de comprobante y motivo: no dice cómo el cliente elige/deriva el
   producto. La prueba rellena un selector `#producto_id` si la UI lo expone; si la UI lo deriva
   internamente, también pasa. Falta precisión en la spec.
2. `motivo_falla` es "requerido si falla", pero el contrato no define respuesta si falta. No se
   escribió aserción para no inventar comportamiento.
3. El caso §5 "cualquier payload que intente forzar `accion:'reembolso'`" no fija el endpoint que
   recibe ese payload; se asumió `POST /api/v1/reclamos/{id}/reembolso` con cuerpo JSON.
4. La forma de los ítems de `GET /api/v1/reclamos` no está especificada; las aserciones usan `id` y
   `pedido_origen_numero`, campos que el contrato sí define para el registro/detalle.
5. "Motorizado puede consultar reclamos asignados a su ruta": no hay asignación observable de
   reclamos a motorizado en el contrato (sí la hay de pedidos en HU-08).

## 7. Alcance respetado

- TESTER solo modificó `backend/tests/test_hu09_reclamos.py`, `frontend/tests/Reclamos.test.tsx` e
  `informes/TESTER-HU-09.md`.
- No se leyó ni modificó `backend/src/modules/reclamos/**`, `backend/src/main.py`,
  `backend/alembic/versions/0006_create_reclamos.py` ni las pantallas del DEV.
- No se publicó: sin push ni merge.

## 8. Archivos

- `backend/tests/test_hu09_reclamos.py`
- `frontend/tests/Reclamos.test.tsx`
- `informes/TESTER-HU-09.md`
