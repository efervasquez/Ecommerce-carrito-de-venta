# Informe de Entrega — TESTER (HU-09)

**Unidad:** HU-09 — Reclamos por producto en mal estado, logística inversa en campo y política de cero reembolsos (FEATURE)
**Documento base:** `contratos/CONTRATO-HU-09.md` (v2, aprobado 2026-11-26, commit `5b0aab0`)
**Rama:** `feat/hu-09-logistica-inversa`
**Autor:** Agente TESTER
**Entrada:** contrato v2 + tipo feature + rutas TESTER asignadas. No se inspeccionó la implementación del DEV.

## 1. Cobertura

Pruebas de caja negra contra la interfaz observable del contrato:

- RBAC y sesión en `/api/v1/reclamos*` (401 sin JWT; 403 de cliente en inspección).
- Registro multipart con evidencias obligatorias y validaciones exactas (fotos, formato, estado del pedido, pertenencia del pedido/producto, arrepentimiento).
- Creación automática del pedido de reposición `BL-REP-...`, monto `0.00`, `PEN`, `delivery`, `Registrado` y compromiso de 1 unidad de stock.
- Inspección física en campo: conformidad (3 checks), conformidad incompleta, falla sin motivo (v2), fallas secuenciales 1–3, escalado a supervisión, bloqueo de inspecciones en estado final y liberación de stock al escalar.
- Asignación de motorizado heredada del pedido de reposición `BL-REP-...` (v2): antes de asignar no ve el reclamo, después sí.
- Bloqueo de reembolso con **HTTP 405** exacto (v2) y de acción forzada `accion:"reembolso"` (422/400).
- Consulta: cliente solo ve sus reclamos; admin ve todos y filtra por `estado` y `pedido_numero`; estructura de ítem del listado definida en v2; reclamo ajeno → 404.
- Frontend: `/reclamos/nuevo?pedido_numero=...` con selector de `producto_id` (v2), historial `/reclamos` y panel admin `/backoffice/reclamos`.

## 2. Matriz Backend (`backend/tests/test_hu09_reclamos.py`)

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| §1 Sin sesión → 401 (todos los endpoints) | `TestRBAC::test_sin_sesion_retorna_401` (5 parámetros) | PASS (5) |
| §1 Cliente no inspecciona → 403 | `TestRBAC::test_cliente_no_puede_registrar_inspeccion_en_campo` | PASS |
| §2 Camino feliz → 201 + reposición + stock | `TestRegistro::test_camino_feliz_crea_reclamo_y_pedido_de_reposicion` | PASS |
| §2 Falta foto producto → 422 | `TestRegistro::test_falta_foto_producto_retorna_422` | PASS |
| §2 Falta foto comprobante → 422 | `TestRegistro::test_falta_foto_comprobante_retorna_422` | PASS |
| §2 Formato inválido → 422 | `TestRegistro::test_formato_de_archivo_invalido_retorna_422` (2 parámetros) | PASS (2) |
| §2 Pedido no entregado → 409 | `TestRegistro::test_pedido_no_entregado_retorna_409` | PASS |
| §2 Pedido ajeno → 404 | `TestRegistro::test_pedido_de_otro_cliente_retorna_404` | PASS |
| §2 Pedido inexistente → 404 | `TestRegistro::test_pedido_inexistente_retorna_404` | PASS |
| §2 Producto ajeno al pedido → 422 | `TestRegistro::test_producto_que_no_pertenece_al_pedido_retorna_422` | PASS |
| §2 Motivo arrepentimiento → 422 | `TestRegistro::test_motivo_de_arrepentimiento_retorna_422` (3 parámetros) | 2 PASS / **1 FAIL** (ver §5) |
| §4 Conforme + 3 checks → `cerrado_exitoso` + reposición `Entregado` | `TestInspeccionCampo::test_conforme_completa_cambio_y_entrega_reposicion` | PASS |
| §4 Conforme incompleto → 422 | `TestInspeccionCampo::test_conforme_con_check_en_false_retorna_422` (3 parámetros) | PASS (3) |
| §4 **Falla sin motivo → 422 (v2)** | `TestInspeccionCampo::test_falla_sin_motivo_retorna_422` | PASS |
| §4 Falla 1/2/3 → reintento y escalado + stock liberado + 409 posterior | `TestInspeccionCampo::test_fallas_secuenciales_escalan_al_tercer_intento` | PASS |
| §4 Reintento sobre cerrado → 409 | `TestInspeccionCampo::test_reintento_sobre_reclamo_cerrado_retorna_409` | PASS |
| §5 Reembolso bloqueado → **405 (v2)** | `TestCeroReembolsos::test_solicitud_de_reembolso_esta_bloqueada` | PASS |
| §5 `accion:"reembolso"` → 422/400 | `TestCeroReembolsos::test_payload_que_fuerza_accion_reembolso_retorna_400_o_422` | PASS |
| §6 Listado cliente solo propio + esquema v2 | `TestConsulta::test_cliente_solo_ve_sus_propios_reclamos` | PASS |
| §6 Listado admin + filtros + esquema v2 | `TestConsulta::test_admin_lista_todos_y_filtra_por_estado_y_pedido` | PASS |
| §6 Reclamo ajeno → 404 | `TestConsulta::test_reclamo_ajeno_retorna_404` | PASS |
| §1/§3 **Motorizado ve reclamo al asignar `BL-REP-...` (v2)** | `TestAsignacionMotorizado::test_motorizado_ve_el_reclamo_al_asignarse_su_pedido_de_reposicion` | PASS |
| §3 `merma_averiada` | `TestNoVerificado::test_merma_averiada_asentada` | SKIP (sin interfaz observable) |
| §4 Bloqueo de nuevos despachos | `TestNoVerificado::test_despachos_bloqueados_tras_escalar` | SKIP (sin código/mensaje pactado) |

## 3. Matriz Frontend (`frontend/tests/Reclamos.test.tsx`)

| Pantalla / comportamiento | Prueba | Resultado |
|---|---|---|
| `/reclamos/nuevo`: precarga pedido, **selector de producto_id (v2)**, motivo y 2 evidencias | `precarga el pedido y exige selector de producto, motivo y las dos evidencias` | PASS |
| `/reclamos/nuevo`: POST multipart con pedido, **producto_id**, motivo y ambas fotos | `envía el reclamo por multipart con pedido, producto, motivo y las dos evidencias` | PASS |
| `/reclamos`: historial del cliente con estados | `muestra los reclamos del cliente con su estado` | PASS |
| `/backoffice/reclamos`: todos los reclamos + incidencias escaladas | `muestra todos los reclamos y las incidencias escaladas` | PASS |
| `/backoffice/reclamos`: filtro por `estado` | `filtra por estado escalado_supervision` | PASS |

## 4. Evidencia de ejecución

### Backend (RabbitMQ arriba, `127.0.0.1:5672`)

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_hu09_reclamos.py -q -c backend/tests/pytest.ini
1 failed, 30 passed, 2 skipped in 361.78s (0:06:01)
```

Única falla (rojo real, pendiente de arbitraje):

```text
TestRegistro::test_motivo_de_arrepentimiento_retorna_422[Quiero devolverlo porque ya no lo necesito]
AssertionError: assert 201 == 422
respuesta: {"id":21, ... "estado":"aprobado", ...}
```

El reclamo se registra (201) cuando el motivo expresa arrepentimiento sin usar las palabras
"arrepentí"/"error en la compra": «Quiero devolverlo porque ya no lo necesito». El contrato §2
exige 422 cuando el motivo **indica** arrepentimiento, pero no enumera frases; se deja el rojo para
que el LEAD arbitre (ampliar la detección del DEV o acotar las frases en la spec). No se aflojó la
prueba.

Requisito de entorno: `python-multipart>=0.0.9` (declarado en `backend/requirements.txt`) no estaba
instalado en `backend/.venv`; se instaló para que la app importe y la suite corra.

### Frontend

```text
cd frontend
npx vitest run tests/Reclamos.test.tsx --reporter=basic
Test Files  1 passed (1)
Tests       5 passed (5)

npx vitest run --reporter=basic          # suite completa, regresión
Test Files  15 passed (15)
Tests       59 passed (59)
```

## 5. Rojo abierto y NO VERIFICADO

1. **Arrepentimiento no detectado** (rojo): «Quiero devolverlo porque ya no lo necesito» se registra
   con 201. Pendiente de arbitraje LEAD (ver §4).
2. **`merma_averiada`**: el contrato exige asentar el producto recogido, pero sigue sin definir
   endpoint ni campo observable. No se fuerza por dentro (regla del playbook).
3. **Bloqueo de nuevos despachos tras escalar**: el contrato habla de "nuevos despachos
   automáticos" pero no fija código HTTP ni mensaje. El efecto verificable (devolución de la unidad
   al stock) sí se cubre en `test_fallas_secuenciales_escalan_al_tercer_intento`.
4. **Inspección física en la UI `/despacho` (3 checks)**: el contrato v2 mantiene la pantalla, pero
   no define cómo obtiene el reclamo asignado ni nombres de campos. Fuera de esta prueba de caja
   negra (`Reclamos.test.tsx`).
5. **`tipo="reposicion"`**: el detalle de pedido de HU-07 no expone `tipo`; se verifica el prefijo
   `BL-REP-`, `monto 0.00`, `PEN`, `delivery`, `Registrado` y el ítem, y se asserta `tipo` solo si la
   respuesta lo incluye.

## 6. Aclaraciones v2 incorporadas

| Aclaración v2 | Cambio en las pruebas | Resultado |
|---|---|---|
| Selector de `producto_id` en `/reclamos/nuevo` | Frontend: exige selector `#producto_id`/`[name=producto_id]` con el producto del pedido y asserta `producto_id` en el FormData | PASS |
| `motivo_falla` obligatorio con 422 | Backend: `test_falla_sin_motivo_retorna_422` con mensaje exacto | PASS |
| HTTP 405 en reembolso | Backend: se exige exactamente 405 (ya no 400/405) | PASS |
| Esquema de ítem en `GET /api/v1/reclamos` | Backend: `assert_estructura_listado` valida los 7 campos en todas las listas | PASS |
| Asignación de motorizado vinculada al `BL-REP-...` | Backend: `TestAsignacionMotorizado` (no ve antes, ve después de `POST /despacho/asignaciones`) | PASS |

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
