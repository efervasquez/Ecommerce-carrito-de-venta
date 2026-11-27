# Informe de Veredicto — HU-11 Reportería y métricas del Backoffice para administradores y supervisores

**Fecha:** 2026-11-27  
**Documento base:** `contratos/CONTRATO-HU-11.md` v1, aprobado por usuario humano  
**Tipo:** Feature  
**Rama:** `feat/hu-11-reporteria-backoffice`  
**Entregas:** TESTER `07c4b88`; DEV `2dd84b9`  
**Árbitro:** LEAD  

---

## 1. Dictamen

**APROBADO.**

- Backend HU-11: **20/20 PASS** en `backend/tests/test_hu11_reportes_backoffice.py` (25.18s).
- Frontend HU-11: **4/4 PASS** en `frontend/tests/ReportesBackoffice.test.tsx` (582ms).
- Frontend Suite Completa (regresión total HU-01 a HU-11): **17/17 archivos, 68/68 tests PASS** (22.48s).
- Typecheck TypeScript (`tsc --noEmit`): **exitoso sin errores**.
- Arbitraje: **0 vueltas necesarias**. Ambas entregas se acoplaron de forma limpia a la primera iteración sobre el contrato observable v1.

---

## 2. Matriz backend (HU-11)

Ejecución: `pytest backend/tests/test_hu11_reportes_backoffice.py -q -c backend/tests/pytest.ini` → `20 passed in 25.18s`.

| Área | Casos del contrato | Resultado |
|---|---|---|
| **RBAC** | Sin sesión → 401 en los 3 endpoints (`/ventas`, `/pedidos-balance`, `/inventario-critico`) | **PASS** |
| **RBAC** | Rol `motorizado` → 403 exacto: `{"detail": "Acceso restringido a administradores y supervisores."}` | **PASS** |
| **RBAC** | Rol `cliente` → 403 exacto: `{"detail": "Acceso restringido a administradores y supervisores."}` | **PASS** |
| **RBAC** | Rol `admin` → 200 en los 3 endpoints | **PASS** |
| **Ventas (GET)** | Rango válido de fechas → 200 con estructura `{fecha_inicio, fecha_fin, total_ordenes, unidades_vendidas, monto_total_facturado, moneda: "PEN"}` | **PASS** |
| **Ventas (GET)** | Rango futuro sin pedidos → 200 con ceros y moneda `PEN` | **PASS** |
| **Ventas (GET)** | Validación `fecha_fin < fecha_inicio` → 422: `{"detail": "La fecha de fin no puede ser anterior a la fecha de inicio."}` | **PASS** |
| **Ventas (GET)** | Validación de formato no ISO (ej. `31-10-2026`) → 422: `{"detail": "El formato de fecha debe ser YYYY-MM-DD."}` | **PASS** |
| **Ventas (GET)** | Sin parámetros de fecha → 200 toma rango por defecto (mes en curso) consistente | **PASS** |
| **Balance (GET)** | Retorna balance con exactamente los 4 estados (`Registrado`, `Preparando producto`, `En camino`, `Entregado`) y `total_pedidos` = suma de los 4 | **PASS** |
| **Balance (GET)** | Pedido confirmado por el flujo transaccional aparece contabilizado en `Registrado` | **PASS** |
| **Inventario (GET)** | Estructura de reporte crítico con claves `stock_bajo`, `quiebres` y `mayor_rotacion` | **PASS** |
| **Inventario (GET)** | Invariante de umbral: todo producto en `stock_bajo` tiene estrictamente `stock_disponible < 6` | **PASS** |
| **Inventario (GET)** | Invariante de quiebre: todo producto en `quiebres` tiene exactamente `stock_disponible == 0` | **PASS** |
| **Inventario (GET)** | Invariante de rotación: `mayor_rotacion` presenta `unidades_vendidas` como entero no negativo | **PASS** |

---

## 3. Matriz frontend

Ejecución: `npx vitest run --reporter=basic` (desde `frontend`) → `Test Files 17 passed (17)`, `Tests 68 passed (68)`.

| Pantalla / Comportamiento | Prueba / Aserción | Resultado |
|---|---|---|
| `/backoffice/reportes` | Renderiza el selector de rango de fechas y tarjetas de totales de ventas | **PASS** |
| `/backoffice/reportes` | Realiza la consulta reactiva con el rango de fechas seleccionado | **PASS** |
| `/backoffice/reportes` | Visualiza las tarjetas de balance con los 4 estados del ciclo de vida | **PASS** |
| `/backoffice/reportes` | Muestra las tablas detalladas de stock bajo, quiebres de inventario y mayor rotación | **PASS** |
| **Regresión completa** | HU-01 a HU-10 (Autenticación, Catálogo, Carrito, OCR, Checkout, Despacho, Reclamos, Contingencia de Inventario) | **PASS (64/64)** |

---

## 4. Arbitraje y ciclo de resolución

- **Alineación inmediata:** No se requirieron rondas de arbitraje correctivo. Tanto DEV como TESTER interpretaron fielmente la especificación y los invariantes observables de `CONTRATO-HU-11.md`.
- **Aclaraciones de huecos:**
  1. *Ventas confirmadas:* DEV consideró los pedidos confirmados transaccionalmente (`tipo != "reposicion"`), excluyendo devoluciones/reposiciones, lo cual fue validado con precisión por TESTER.
  2. *Solapamiento de stock bajo y quiebres:* Un producto con existencia `0` pertenece simultáneamente a `quiebres` (`disponible == 0`) y a `stock_bajo` (`disponible < 6`), satisfaciendo las aserciones de caja negra.
  3. *Arquitectura CQRS:* Consultas de agregación SQL puras de solo lectura sobre las tablas maestras con logs estructurados que inyectan `reporte`, `usuario_id` y timestamp.
- **Sin trampas ni atajos:**
  - DEV no alteró pruebas del TESTER ni modificó rutas fuera de su alcance.
  - TESTER no aflojó aserciones ni acopló sus pruebas a detalles internos de implementación.

---

## 5. Propiedad de rutas

Auditoría estricta de commits en la rama (`git log 299feeb^..HEAD --name-status`):

| Commit | Rol | Prefijo | Rutas tocadas | ¿Conforme a AGENTS.md? |
|---|---|---|---|---|
| `299feeb` | LEAD | `[LEAD]` | `contratos/CONTRATO-HU-11.md` | ✅ Sí |
| `07c4b88` | TESTER | `[TESTER]` | `backend/tests/**`, `frontend/tests/**`, `informes/TESTER-HU-11.md` | ✅ Sí |
| `2dd84b9` | DEV | `[DEV]` | `backend/src/**`, `frontend/src/**`, `informes/DEV-HU-11.md` | ✅ Sí |

---

## 6. Conclusión

La unidad de trabajo **HU-11** cumple rigurosamente con su contrato observable v1, los criterios de aceptación, las directrices de seguridad y RBAC, y la suite completa de regresión sin defectos. Se autoriza la apertura del Pull Request hacia la rama principal.
