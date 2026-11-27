# Informe de Veredicto — HU-10 Contingencia de inventario, alta y edición integral de productos

**Fecha:** 2026-11-26  
**Documento base:** `contratos/CONTRATO-HU-10.md` v1, aprobado por usuario humano  
**Tipo:** Feature  
**Rama:** `feat/hu-10-contingencia-stock`  
**Entregas:** TESTER `4f0fb8d`; DEV `3383048` + `7e6acbd`  
**Árbitro:** LEAD  

---

## 1. Dictamen

**APROBADO.**

- Backend HU-10: **37/37 PASS** en `backend/tests/test_hu10_contingencia_stock.py` (18.61s).
- Frontend HU-10: **5/5 PASS** en `frontend/tests/InventarioContingencia.test.tsx`.
- Frontend Suite Completa (regresión HU-01 a HU-10): **16/16 archivos, 64/64 tests PASS** (20.13s).
- Typecheck TypeScript (`tsc --noEmit`): **exitoso sin errores**.
- Arbitraje: 1 vuelta completada favorablemente (ajuste de `id=producto_id` en `StockAjusteResponse` en DEV `7e6acbd`).

---

## 2. Matriz backend (HU-10)

Ejecución: `pytest backend/tests/test_hu10_contingencia_stock.py -q -c backend/tests/pytest.ini` → `37 passed in 18.61s`.

| Área | Casos del contrato | Resultado |
|---|---|---|
| **RBAC** | Sin sesión → 401 en todos los endpoints del backoffice de productos | **PASS** |
| **RBAC** | Rol `cliente` o `motorizado` → 403 con mensaje exacto contractual: `"Acceso restringido a operadores de inventario y administradores."` | **PASS** |
| **Alta (POST)** | Ficha completa con existencias iniciales → 201 + persistencia en `productos` e `inventario_stock` | **PASS** |
| **Alta (POST)** | Existencias negativas o no enteras (`-1`, `12.5`) → 422 con mensaje exacto | **PASS** |
| **Alta (POST)** | Precio regular `<= 0` (`0`, `-5.0`) → 422 con mensaje exacto | **PASS** |
| **Alta (POST)** | Descuento fuera del rango 0..100 (`-1`, `101`) → 422 con mensaje exacto | **PASS** |
| **Alta (POST)** | Métodos de entrega inválidos (distintos de `delivery` y `retiro`) → 422 con mensaje exacto | **PASS** |
| **Alta (POST)** | Campos obligatorios omitidos → 422 contractual | **PASS** |
| **Listado (GET)** | Listado paginado con filtro `q` por nombre o componente activo → 200 `{items, total}` | **PASS** |
| **Listado (GET)** | Esquema exacto de 9 campos por ítem (`id`, `nombre`, `componentes`, `precio_regular`, `descuento_porcentaje`, `stock_disponible`, `stock_reservado`, `precios_bajos`, `requiere_receta`) | **PASS** |
| **Detalle (GET)** | Consulta por ID existente → 200 con ficha comercial/clínica integral y existencias | **PASS** |
| **Detalle (GET)** | Consulta por ID inexistente → 404 | **PASS** |
| **Edición (PUT)** | Edición de atributos comerciales, clínicos, descuento y flag de Precios Bajos → 200 sin alterar existencias | **PASS** |
| **Edición (PUT)** | Validaciones de precio, descuento y métodos en edición → 422 | **PASS** |
| **Edición (PUT)** | Intento de edición sobre producto inexistente → 404 | **PASS** |
| **Ajuste Stock (PATCH)** | Ajuste manual de existencias → 200 `{id: producto_id, producto_id, disponible, reservado, actualizado_en}` | **PASS** |
| **Ajuste Stock (PATCH)** | Auditoría registrada en tabla `inventario_ajustes` (`producto_id`, `usuario_id`, `stock_anterior`, `stock_nuevo`, `motivo`, timestamp) | **PASS** |
| **Ajuste Stock (PATCH)** | Ajuste conserva el stock reservado existente sin alterarlo | **PASS** |
| **Ajuste Stock (PATCH)** | Validación de stock no entero o negativo en ajuste → 422 sin mutar stock | **PASS** |
| **Ajuste Stock (PATCH)** | Ajuste sobre producto inexistente → 404 | **PASS** |

---

## 3. Matriz frontend

Ejecución: `npx vitest run --reporter=basic` (desde `frontend`) → `Test Files 16 passed (16)`, `Tests 64 passed (64)`.

| Pantalla / Comportamiento | Prueba / Aserción | Resultado |
|---|---|---|
| `/backoffice/inventario` | Muestra tabla de existencias con stock disponible y reservado | **PASS** |
| `/backoffice/inventario` | Buscador interactivo filtra productos por nombre y componente | **PASS** |
| `/backoffice/inventario` | Ajuste rápido de stock por fila con botón Guardar y confirmación visual | **PASS** |
| `/backoffice/inventario/nuevo` | Formulario de alta completo con captura de stock inicial | **PASS** |
| `/backoffice/inventario/:id/editar` | Formulario de edición con precarga y selector manual de Precios Bajos | **PASS** |
| **Regresión completa** | HU-01 a HU-09 (Autenticación, Catálogo, Carrito, OCR, Checkout, Despacho, Reclamos) | **PASS (59/59)** |

---

## 4. Arbitraje y ciclo de resolución

- **Rojo detectado (Vuelta 1):**
  - Prueba afectada: `backend/tests/test_hu10_contingencia_stock.py::TestAjusteStock::test_camino_feliz_actualiza_disponible_y_devuelve_reservado`.
  - Error: `AssertionError: assert body["id"] == producto["id"] (assert 555 == 12)`.
  - Causa raíz: En `backend/src/modules/inventario/service.py` línea 267, `StockAjusteResponse` mapeaba `id=stock.id` (555, PK de la fila en `inventario_stock`) en vez de `id=producto_id` (12, recurso del producto ajustado en la URI `/api/v1/backoffice/productos/{id}/stock`).
  - Arbitraje LEAD: **Se apartó el código**. El contrato observable especifica explícitamente:
    `Respuesta 200: { "id": 12, "producto_id": 12, "disponible": 45, "reservado": 2, "actualizado_en": ... }`.
  - Devolución a DEV: Asignar `id=producto_id` en la respuesta.
  - Corrección DEV: Commit `7e6acbd`.
  - Re-ejecución LEAD: **37/37 PASS** en 18.61s.
- **Sin trampas ni atajos:**
  - DEV no alteró pruebas del TESTER ni modificó rutas fuera de su alcance.
  - TESTER mantuvo las validaciones de caja negra estrictas.
  - Integridad de base de datos verificada con migración `0007_create_productos_contingencia.py` y rollback limpio.

---

## 5. Propiedad de rutas

Auditoría estricta de commits en la rama (`git log fc5c3a0^..HEAD --name-status`):

| Commit | Rol | Prefijo | Rutas tocadas | ¿Conforme a AGENTS.md? |
|---|---|---|---|---|
| `fc5c3a0` | LEAD | `[LEAD]` | `contratos/CONTRATO-HU-10.md` | ✅ Sí |
| `4f0fb8d` | TESTER | `[TESTER]` | `backend/tests/**`, `frontend/tests/**`, `informes/TESTER-HU-10.md` | ✅ Sí |
| `3383048` | DEV | `[DEV]` | `backend/alembic/**`, `backend/src/**`, `frontend/src/**`, `informes/DEV-HU-10.md` | ✅ Sí |
| `7e6acbd` | DEV | `[DEV]` | `backend/src/modules/inventario/service.py` | ✅ Sí |

---

## 6. Conclusión

La unidad de trabajo **HU-10** cumple rigurosamente con su contrato observable v1, los criterios de aceptación, las políticas de arquitectura y seguridad del proyecto, y la suite completa de regresión. Se autoriza la apertura del Pull Request hacia la rama principal.
