# Informe de Veredicto — HU-09 Logística inversa, reclamos en campo y política de cero reembolsos

**Fecha:** 2026-11-26  
**Documento base:** `contratos/CONTRATO-HU-09.md` v2, aprobado por usuario humano  
**Tipo:** Feature  
**Rama:** `feat/hu-09-logistica-inversa`  
**Entregas:** TESTER `fb38c15` + `242e241`; DEV `4d66ce0` + `d50bfa0`  
**Árbitro:** LEAD  

---

## 1. Dictamen

**APROBADO.**

- Backend HU-09: **31 PASS / 2 SKIPPED (TestNoVerificado)** en `backend/tests/test_hu09_reclamos.py`.
- Frontend HU-09: **5/5 PASS** en `frontend/tests/Reclamos.test.tsx`.
- Frontend Suite Completa (regresión HU-01 a HU-09): **15/15 archivos, 59/59 tests PASS**.
- Typecheck TypeScript (`tsc --noEmit`): **exitoso sin errores**.
- Arbitraje: 1 vuelta completada favorablemente (ampliación de términos de arrepentimiento en DEV `d50bfa0`).

---

## 2. Matriz backend (HU-09)

Ejecución: `pytest backend/tests/test_hu09_reclamos.py -q -c backend/tests/pytest.ini` → `31 passed, 2 skipped`.

| Área | Casos del contrato | Resultado |
|---|---|---|
| **RBAC** | Sin sesión → 401 en todos los endpoints de reclamos (5 endpoints) | **PASS** |
| **RBAC** | Rol `cliente` no puede inspeccionar en campo → 403 | **PASS** |
| **Registro** | Camino feliz → 201 + `Reclamo` aprobado + `Pedido` reposición `BL-REP-...` (0.00, PEN, delivery) + descuento de stock | **PASS** |
| **Registro** | Falta `foto_producto` → 422 con mensaje exacto | **PASS** |
| **Registro** | Falta `foto_comprobante` → 422 con mensaje exacto | **PASS** |
| **Registro** | Formato de archivo inválido → 422 | **PASS** |
| **Registro** | Pedido no entregado → 409 | **PASS** |
| **Registro** | Pedido ajeno → 404 | **PASS** |
| **Registro** | Pedido inexistente → 404 | **PASS** |
| **Registro** | Producto ajeno al pedido → 422 | **PASS** |
| **Registro** | Motivos de arrepentimiento/desistimiento → 422 (3 variantes verificadas tras vuelta 1) | **PASS** |
| **Inspección** | Conforme con 3 checks → `cerrado_exitoso` + reposición `Entregado` | **PASS** |
| **Inspección** | Conforme incompleto (algún check en false) → 422 | **PASS** |
| **Inspección** | Falla sin motivo de falla (v2) → 422 con mensaje exacto | **PASS** |
| **Inspección** | Fallas secuenciales 1, 2 y 3 → reintentos, escalado a supervisión, bloqueo de inspección posterior y devolución de stock al disponible | **PASS** |
| **Inspección** | Reintento sobre reclamo ya cerrado o escalado → 409 | **PASS** |
| **Cero reembolsos** | Intento de reembolso vía `POST .../reembolso` → 405 Method Not Allowed (v2) | **PASS** |
| **Cero reembolsos** | Payload forzado con `accion: "reembolso"` → 400/422 con mensaje de política estricta | **PASS** |
| **Consulta** | Cliente solo ve sus propios reclamos | **PASS** |
| **Consulta** | Admin lista todos y filtra por `estado` y `pedido_numero` | **PASS** |
| **Consulta** | Estructura de ítem del listado estandarizada a 7 campos v2 | **PASS** |
| **Consulta** | Reclamo ajeno → 404 | **PASS** |
| **Asignación** | Motorizado ve el reclamo solo al asignarse el pedido de reposición `BL-REP-...` en despacho | **PASS** |
| **No observable** | Asiento de `merma_averiada` en BD interna | **SKIPPED (NO VERIFICADO)** |
| **No observable** | Bloqueo de programación de 4to despacho tras escalar | **SKIPPED (NO VERIFICADO)** |

### Justificación de casos NO VERIFICADO
1. **Asiento interno de `merma_averiada`:** La tabla se crea y persiste en el backend (`0006_create_reclamos.py` y `MermaAveriada`), pero no existe un endpoint de consulta pública de mermas en la API de caja negra.
2. **Bloqueo de 4to despacho:** No existe un endpoint directo para forzar un despacho manual adicional. El efecto observable exigido (retorno del producto nuevo al stock disponible y pase a `escalado_supervision`) está 100% verificado.

---

## 3. Matriz frontend

Ejecución: `npx vitest run --reporter=basic` (desde `frontend`) → `Test Files 15 passed (15)`, `Tests 59 passed (59)`.

| Pantalla / Comportamiento | Prueba / Aserción | Resultado |
|---|---|---|
| `/reclamos/nuevo` | Precarga pedido, selector de `producto_id`, motivo y 2 evidencias | **PASS** |
| `/reclamos/nuevo` | Envío de formulario multipart con campos requeridos | **PASS** |
| `/reclamos` | Historial del cliente con estados de reclamo | **PASS** |
| `/backoffice/reclamos` | Todos los reclamos y visualización destacada de incidencias escaladas | **PASS** |
| `/backoffice/reclamos` | Filtro reactivo por estado (`escalado_supervision`) | **PASS** |
| **Regresión completa** | HU-01 (Login, Registro, Activación), HU-02 (Recuperación), HU-03 (Catálogo), HU-04 (Detalle), HU-05 (Carrito), HU-06 (OCR), HU-07 (Checkout/Stripe), HU-08 (Despacho) | **PASS (54/54)** |

---

## 4. Arbitraje y ciclo de resolución

- **Aclaraciones de spec (v2):** El TESTER reportó 5 puntos abiertos iniciales. El LEAD los escaló al humano, quien los aprobó formalmente. Se emitió `CONTRATO-HU-09.md` v2 (commit `5b0aab0`) incorporando el selector de `producto_id`, validación 422 de `motivo_falla`, 405 para reembolso, estructura del listado y asignación por `BL-REP-...`.
- **Rojo de arrepentimiento (Vuelta 1):** El test evaluó la frase «Quiero devolverlo porque ya no lo necesito». DEV devolvía 201 porque su lista de detección era estricta. El LEAD arbitró con la spec en mano (§2: motivo indica error de compra, equivocación o arrepentimiento → 422): **se apartó el código**.
  - Devolución a DEV: ampliar `_TERMINOS_ARREPENTIMIENTO`.
  - DEV corrigió en commit `d50bfa0`.
  - Re-ejecución LEAD: **3/3 PASS** en 38.57s.
- **Sin trampas ni atajos:**
  - DEV no tocó ningún archivo en `backend/tests/**` ni `frontend/tests/**`.
  - TESTER no modificó las reglas contractuales ni aflojó aserciones para forzar el verde.
  - El código cumple con transaccionalidad atómica SQLAlchemy y manejo de archivos mediante UUID en `./uploads/reclamos/`.

---

## 5. Propiedad de rutas

Auditoría estricta de commits en la rama (`git log bf757e7..HEAD --name-only`):

| Commit | Rol | Prefijo | Rutas tocadas | ¿Conforme a AGENTS.md? |
|---|---|---|---|---|
| `5b0aab0` | LEAD | `[LEAD]` | `contratos/CONTRATO-HU-09.md` | ✅ Sí |
| `fb38c15` | TESTER | `[TESTER]` | `backend/tests/**`, `frontend/tests/**`, `informes/TESTER-HU-09.md` | ✅ Sí |
| `4d66ce0` | DEV | `[DEV]` | `backend/alembic/**`, `backend/src/**`, `frontend/src/**`, `informes/DEV-HU-09.md` | ✅ Sí |
| `242e241` | TESTER | `[TESTER]` | `backend/tests/**`, `frontend/tests/**`, `informes/TESTER-HU-09.md` | ✅ Sí |
| `d50bfa0` | DEV | `[DEV]` | `backend/src/modules/reclamos/service.py` | ✅ Sí |

---

## 6. Conclusión

La unidad de trabajo **HU-09** cumple rigurosamente con su contrato observable v2, las políticas de arquitectura y seguridad del proyecto, y las pruebas de regresión. Se autoriza la integración mediante Pull Request hacia la rama principal.
