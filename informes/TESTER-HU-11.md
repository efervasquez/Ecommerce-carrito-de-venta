# Informe de Entrega — TESTER (HU-11)

**Unidad:** HU-11 — Reportería y métricas del Backoffice para administradores y supervisores (FEATURE)
**Documento base:** `contratos/CONTRATO-HU-11.md` (v1, aprobado 2026-11-26)
**Rama:** `feat/hu-11-reporteria-backoffice`
**Autor:** Agente TESTER
**Entrada:** contrato v1 + tipo feature + rutas TESTER asignadas. No se inspeccionó la implementación del DEV.

## 1. Cobertura

Pruebas de caja negra contra la interfaz observable del contrato:

- RBAC: 401 sin JWT en los 3 endpoints; 403 exacto para motorizado (3) y cliente (3); 200 para admin (3).
- Ventas: estructura exacta del camino feliz, eco de fechas, moneda PEN, totales no negativos; rango futuro sin pedidos → ceros; `fecha_fin < fecha_inicio` → 422; formato no ISO (3 variantes) → 422; sin parámetros → rango por defecto válido y ordenado.
- Balance: exactamente los 4 estados, conteos enteros no negativos y `total_pedidos` = suma; un pedido confirmado por el flujo real HU-07 aparece en `Registrado`.
- Inventario crítico: estructura, `stock_bajo` estrictamente `< 6`, `quiebres` con stock 0, `mayor_rotacion` con `unidades_vendidas` entero no negativo.
- Frontend: `/backoffice/reportes` con selector de fechas y totales, consulta con el rango elegido, balance de los 4 estados y tablas de inventario crítico.

## 2. Matriz Backend (`backend/tests/test_hu11_reportes_backoffice.py`)

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| §1 Sin sesión → 401 (3 endpoints) | `TestRBAC::test_sin_sesion_retorna_401` (3 parámetros) | NO EJECUTADA (app no importable aún) |
| §1 Motorizado → 403 exacto (3 endpoints) | `TestRBAC::test_motorizado_retorna_403` (3 parámetros) | NO EJECUTADA (app no importable aún) |
| §1 Cliente → 403 exacto (3 endpoints) | `TestRBAC::test_cliente_retorna_403_en_los_tres_reportes` | NO EJECUTADA (app no importable aún) |
| §1 Admin → 200 (3 endpoints) | `TestRBAC::test_admin_retorna_200` (3 parámetros) | NO EJECUTADA (app no importable aún) |
| §2 Ventas: estructura y eco de fechas | `TestVentas::test_rango_valido_devuelve_la_estructura_del_contrato` | NO EJECUTADA (app no importable aún) |
| §2 Ventas: rango futuro sin pedidos → ceros | `TestVentas::test_rango_futuro_sin_pedidos_devuelve_ceros` | NO EJECUTADA (app no importable aún) |
| §2 Ventas: fecha fin anterior → 422 | `TestVentas::test_fecha_fin_anterior_retorna_422` | NO EJECUTADA (app no importable aún) |
| §2 Ventas: formato inválido → 422 | `TestVentas::test_formato_de_fecha_invalido_retorna_422` (3 parámetros) | NO EJECUTADA (app no importable aún) |
| §2 Ventas: sin fechas → rango por defecto | `TestVentas::test_sin_parametros_toma_un_rango_por_defecto` | NO EJECUTADA (app no importable aún) |
| §3 Balance: 4 estados + total coherente | `TestBalancePedidos::test_balance_incluye_los_cuatro_estados_y_total_coherente` | NO EJECUTADA (app no importable aún) |
| §3 Balance: pedido confirmado en `Registrado` | `TestBalancePedidos::test_pedido_confirmado_aparece_en_registrado` | NO EJECUTADA (app no importable aún) |
| §4 Inventario crítico: estructura e invariantes | `TestInventarioCritico::test_estructura_e_invariantes_de_stock` | NO EJECUTADA (app no importable aún) |

## 3. Matriz Frontend (`frontend/tests/ReportesBackoffice.test.tsx`)

| Pantalla / comportamiento | Prueba | Resultado |
|---|---|---|
| `/backoffice/reportes`: selector de rango + totales de ventas | `muestra el selector de rango y los totales de ventas` | NO EJECUTADA (pantalla aún no existe) |
| `/backoffice/reportes`: consulta con el rango elegido | `consulta el reporte con el rango de fechas elegido` | NO EJECUTADA (pantalla aún no existe) |
| `/backoffice/reportes`: balance de los 4 estados | `muestra los 4 estados del ciclo de vida` | NO EJECUTADA (pantalla aún no existe) |
| `/backoffice/reportes`: tablas de inventario crítico | `muestra las tablas de stock bajo, quiebres y rotación` | NO EJECUTADA (pantalla aún no existe) |

## 4. Evidencia de ejecución

### Backend

```text
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_hu11_reportes_backoffice.py --collect-only -q -c backend/tests/pytest.ini
20 tests collected in 0.14s

pytest ... -k "admin_retorna_200" -rs
SKIPPED [3] Backend application (src.main.app) not yet implemented:
cannot import name 'PedidoBalance' from 'src.modules.reportes.schemas'
```

El módulo `backend/src/modules/reportes/` está en curso (sin commit) y todavía no es importable;
`src.main` falla y el fixture de `conftest.py` marca la suite como NO EJECUTADA. No es un rojo de la
implementación: aún no hay app que probar.

### Frontend

```text
cd frontend
npx vitest run tests/ReportesBackoffice.test.tsx --reporter=basic
Test Files  1 failed (1)
Tests       4 failed (4)
```

Motivo: `src/pages/BackofficeReportes.tsx` todavía no existe; los 4 casos fallan en la carga de la
pantalla (`Pantalla /backoffice/reportes no implementada`). Se entregan escritos.

## 5. Notas de alcance / supuestos

1. **Filtro de estados en ventas**: el contrato dice "órdenes confirmadas" sin precisar si son
   todos los pedidos pagados o solo `Entregado`. No se asserta la inclusión de un pedido `Registrado`;
   la exactitud se valida con un rango futuro sin pedidos (todo en cero). Reportado al LEAD.
2. **Tipos**: `total_ordenes` y `unidades_vendidas` se asumen enteros; `monto_total_facturado`
   numérico ≥ 0 y `moneda` exactamente `PEN`.
3. **Rango por defecto**: el contrato permite "mes en curso o últimos 30 días"; solo se valida que
   ambas fechas sean ISO, existan y estén ordenadas.
4. **`stock_bajo` vs `quiebres`**: el contrato solo exige `< 6` para `stock_bajo` y `0` para
   quiebres; se acepta que un producto con 0 pueda aparecer en ambas listas (solapamiento no
   prohibido).
5. **`mayor_rotacion`**: no se define top-N ni umbral; se valida estructura y tipo, no el orden.
6. **UI**: se asumen inputs `fecha_inicio`/`fecha_fin` (o dos `input[type=date]`) y los 4 nombres de
   estado para el balance. El diseño visual queda a criterio del DEV (fuera del contrato).

## 6. Alcance respetado

- TESTER solo modificó `backend/tests/test_hu11_reportes_backoffice.py`,
  `frontend/tests/ReportesBackoffice.test.tsx` e `informes/TESTER-HU-11.md`.
- No se leyó ni modificó `backend/src/modules/reportes/**`, `backend/src/main.py` ni
  `frontend/src/pages/BackofficeReportes.tsx`.
- No se publicó: sin push ni merge.

## 7. Archivos

- `backend/tests/test_hu11_reportes_backoffice.py`
- `frontend/tests/ReportesBackoffice.test.tsx`
- `informes/TESTER-HU-11.md`
