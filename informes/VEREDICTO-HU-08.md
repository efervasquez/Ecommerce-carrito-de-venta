# Informe de Veredicto — HU-08 Buzón de despacho y ciclo de vida de pedidos

**Fecha:** 2026-11-27
**Documento base:** `contratos/CONTRATO-HU-08.md` v2, aprobado por usuario humano
**Tipo:** Feature
**Rama:** `feat/hu-08-despacho`
**Entregas:** TESTER `956c9ec` + `f07944d`; DEV `b793602`
**Árbitro:** LEAD

## 1. Dictamen

**APROBADO.** Los 3 casos NO VERIFICADO fueron aceptados por el usuario humano (2026-11-27).

- Backend HU-08: **28 PASS / 3 SKIPPED**, estable en **2 corridas consecutivas**.
- Frontend suite completa: **14/14 archivos, 54/54 tests PASS**.
- Build TypeScript/Vite: **exitoso**.
- Regresión backend HU-05+HU-06+HU-07: **55 PASS / 6 SKIPPED**.

## 2. Matriz backend (HU-08)

Ejecución: `pytest tests/test_hu08_despacho.py` → `28 passed, 3 skipped` (x2, 258s y 249s).

| Área | Casos | Resultado |
|---|---|---|
| RBAC — sin sesión | 401 en los 7 endpoints | PASS |
| RBAC — rol `cliente` | 403 en los 7 endpoints | PASS |
| RBAC — admin | Lee buzón y zonas | PASS |
| RBAC — motorizado | No puede asignar lotes | PASS |
| Buzón | Campos del contrato + filtros `estado`/`zona_id` | PASS |
| Consolidación | Conteos por zona/distrito (4 estados) | PASS |
| Asignación válida | Lote `Registrado`→`Preparando producto` con `motorizado_id` | PASS |
| Asignación parcial (estados mezclados) | 409 sin asignación parcial | PASS |
| Asignación — `motorizado_id` inválido | 422/404 | PASS |
| Pendientes | FIFO por llegada | PASS |
| Auto-asignar | El más antiguo → 200; saltarse la fila → 409 | PASS |
| Ciclo de vida | `Preparando producto`→`En camino`→`Entregado` | PASS |
| Salto inválido | 409 con mensaje exacto | PASS |
| Historial | `estado_anterior`, `estado_nuevo`, `usuario_id`, `timestamp` cronológico; 404 inexistente | PASS |
| `incidencia_stock` no transiciona | — | SKIPPED (NO VERIFICADO) |
| Asignación con zonas mezcladas | Requiere 2 zonas en el seed | SKIPPED (NO VERIFICADO) |
| 403 pedido de otro motorizado | Requiere 2 motorizados en el seed | SKIPPED (NO VERIFICADO) |

### Casos NO VERIFICADO (aceptados por el usuario humano, 2026-11-27)

1. `incidencia_stock` no transiciona — provocar una inconsistencia física de almacén no es observable en caja negra.
2. Asignación con **zonas mezcladas** → 409 sin asignación parcial — el seed expone una sola zona; el caso de estados mezclados sí está verificado.
3. 403 para un motorizado que opera un **pedido de otro** motorizado — el seed crea un solo motorizado; el 403 por rol cliente sí está verificado y el pedido ajeno se cubre parcialmente con el 409 de salto inválido.

## 3. Matriz frontend

| Área | Resultado |
|---|---|
| `/backoffice/despacho`: buzón agrupado por zona, conteos, filtro por estado, selección de lote y `POST /despacho/asignaciones` | PASS |
| `/despacho`: pendientes FIFO, auto-asignar, avance `En camino`/`Entregado` y mensaje exacto de 409 | PASS |
| Resto de la suite (HU-01 a HU-07) | PASS |

Ejecución: `npx vitest run` → `Test Files 14 passed (14)`, `Tests 54 passed (54)`; `npm run build` → correcto.

## 4. Arbitraje

- **Flakiness del harness (vuelta 2):** el helper de activación de HU-08 purgaba→cerraba→registraba→reabría y filtraba por email con 60s. Se reemplazó por el patrón estable de `test_hu01_auth.py` (purga inmediata, registro, consumir el siguiente mensaje de `email.auth`) y se añadió reset de estado por prueba. Resultado: 2 corridas consecutivas 28/3 sin fallos.
- **RBAC:** `TestRBAC` pasa 16/16; el fallo previo en la corrida completa era aislamiento/estado, resuelto con el reset por prueba.
- **Desviación aceptada (`GET /api/v1/despacho/pedidos` para motorizado):** el motorizado obtiene **solo sus pedidos**; el buzón completo sigue siendo `admin`. Se reflejó en `CONTRATO-HU-08.md` v2.
- **Sin manipulación de pruebas:** el commit del DEV (`b793602`) no modificó archivos de prueba (verificado con `git diff b793602..HEAD -- backend/tests frontend/tests`: solo pruebas del TESTER).
- **Seguridad:** RBAC por rol (401/403) y seed de `admin`/`motorizado` por variables de entorno, sin defaults hardcodeados en producción.
- **Deuda de infraestructura (preexistente):** la suite backend completa no corre en un solo comando; validada por módulos.

## 5. Propiedad de rutas

- TESTER: `backend/tests/test_hu08_despacho.py`, `frontend/tests/BackofficeDespacho.test.tsx`, `frontend/tests/Despacho.test.tsx`; commits `956c9ec`, `f07944d`.
- DEV: `backend/src/modules/despacho/**`, `backend/alembic/versions/0005_create_despacho.py`, `backend/src/main.py`, `backend/src/config.py`, `backend/src/modules/pagos/models.py`, `backend/.env.example`, `frontend/src/**`, `informes/DEV-HU-08.md`; commit `b793602`.
- LEAD: `contratos/CONTRATO-HU-08.md` v1 (`0bcecbd`) y v2, veredicto.
- No se cometieron artefactos no rastreados (`frontend/dist`, `package.json` raíz, `package-lock.json`).
