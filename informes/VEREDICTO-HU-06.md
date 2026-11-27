# Informe de Veredicto — HU-06 Automatización OCR de recetas médicas

**Fecha:** 2026-11-27
**Documento base:** `contratos/CONTRATO-HU-06.md` v1 (+ `CONTRATO-HU-07.md` v2, bloqueo W-03), aprobado por usuario humano
**Tipo:** Feature
**Rama:** `feat/hu-06-ocr`
**Entregas:** TESTER `ab0928c` + `fb9602a`; DEV `e242b25`
**Árbitro:** LEAD

## 1. Dictamen

**APROBADO.** Los casos NO VERIFICADO fueron aceptados por el usuario humano (2026-11-27).

- Backend HU-06: **17 PASS / 1 SKIPPED**.
- Frontend suite completa: **12/12 archivos, 46/46 tests PASS**.
- Build TypeScript/Vite: **exitoso**.
- Regresión backend HU-05+HU-07: **38 PASS / 5 SKIPPED**.

## 2. Matriz backend (HU-06)

Ejecución: `pytest tests/test_hu06_ocr_recetas.py` → `17 passed, 1 skipped`.

| Caso | Prueba | Resultado |
|---|---|---|
| Subir receta sin sesión → 401 | `test_subir_receta_sin_sesion_retorna_401` | PASS |
| Consultar job sin sesión → 401 | `test_consultar_job_sin_sesion_retorna_401` | PASS |
| Job inexistente → 404 | `test_job_inexistente_retorna_404` | PASS |
| Job ajeno → 404 | `test_job_ajeno_retorna_404` | PASS |
| Subida válida → 202 con `job_id`/`procesando`/`poll_interval_ms=1500` | `test_subida_valida_retorna_202_con_polling` | PASS |
| Formato inválido → 422 mensaje exacto | `test_formato_invalido_retorna_422` | PASS |
| Tamaño excedido → 413 mensaje exacto | `test_tamano_excedido_retorna_413` | PASS |
| `completado`: inserta ítems y asocia `receta_id` | `test_completado_inserta_items_y_asocia_receta` | PASS |
| `requiere_validacion`: sugeridos y confianza, sin insertar | `test_requiere_validacion_expone_sugeridos_sin_insertar` | PASS |
| `sin_stock`: sin inserción parcial (PA-03) y mensaje exacto | `test_sin_stock_no_inserta_parcial_y_mensaje_exacto` | PASS |
| `error`: fallo técnico del motor | `test_estado_error` | PASS |
| Confirmar válido → completa e inserta | `test_confirmar_valido_completa_e_inserta` | PASS |
| Confirmar job sin stock → 409 | `test_confirmar_job_sin_stock_retorna_409` | PASS |
| Confirmar job ya completado → 409 | `test_confirmar_job_ya_completado_retorna_409` | PASS |
| Confirmar job ajeno → 404 | `test_confirmar_job_ajeno_retorna_404` | PASS |
| Checkout bloquea `requiere_receta` sin receta → 409 mensaje exacto | `test_checkout_bloquea_producto_requiere_receta` | PASS |
| Checkout con receta validada continúa HU-07 | `test_checkout_con_receta_validada_continua_hu07` | PASS |
| Borrado del documento original (LPDP) | `test_documento_original_eliminado` | SKIPPED (NO VERIFICADO) |

### Casos NO VERIFICADO (aceptados por el usuario humano, 2026-11-27)

1. `test_documento_original_eliminado` — el borrado del documento tras procesarlo no es observable por la API pública; es una garantía interna de retención (ADR-0015).
2. Extracción real con Tesseract — por la decisión 4 del contrato (aprobada), la caja negra usa un proveedor deterministico (marcadores `receta_ok`/`receta_lowconf`/`receta_nostock`/`receta_error`); la **precisión real del motor OCR no se verifica en CI**. Tesseract no está instalado en la máquina; el proveedor real queda inyectable y documentado.

## 3. Matriz frontend

| Área | Resultado |
|---|---|
| Botón `Leer receta`, subida y polling | PASS |
| Redirección a `/carrito` en `completado` | PASS |
| Modal de validación asistida (`requiere_validacion`) | PASS |
| Alerta `sin_stock` con nombre devuelto por la API | PASS |
| Mensaje de `error` | PASS |
| Resto de la suite (HU-01 a HU-07) | PASS |

Ejecución: `npx vitest run` → `Test Files 12 passed (12)`, `Tests 46 passed (46)`; `npm run build` → correcto.

## 4. Arbitraje

- **Escritura independiente:** el TESTER redactó las pruebas solo desde `CONTRATO-HU-06.md` v1 y `CONTRATO-HU-07.md` v2 (sin ver la implementación) y reportó rojos esperados.
- **Vuelta 1:** se activó el estado `error` mediante el marcador `receta_error.*` (coordinado entre TESTER y DEV). El TESTER además corrigió `test_job_inexistente_retorna_404` para derivar un id inexistente de un id real (antes un formato inválido daba 422); corrección legítima alineada al contrato.
- **Verificación independiente del LEAD:** HU-06 17/1, frontend 46/46, build OK, regresión HU-05+HU-07 38/5.
- **W-03:** el checkout bloquea con 409 `"Debes adjuntar y validar tu receta médica para continuar con el pago"` y continúa con receta validada; `CONTRATO-HU-07` quedó en v2.
- **Privacidad:** solo se conserva el resultado estructurado; el documento original se elimina tras procesar (no observable en caja negra).
- **Dependencias:** `requirements.txt` añade `Pillow`, `pytesseract`, `pypdf`; `.env.example` incluye `TESSERACT_CMD` (ruta, no secreto), `OCR_TEST_MODE`, `OCR_WORKER_ENABLED`, `OCR_POLL_INTERVAL_MS=1500`, `OCR_CONFIDENCE_THRESHOLD=65`.
- **Prerrequisito de despliegue:** instalar el binario de Tesseract en Windows y fijar `TESSERACT_CMD`; sin él, el OCR real no opera (las pruebas usan el proveedor fake).
- **Deuda de infraestructura (preexistente):** suite backend completa no corre en un solo comando; validada por módulos.

## 5. Propiedad de rutas

- TESTER: `backend/tests/test_hu06_ocr_recetas.py`, `frontend/tests/Receta.test.tsx`; commits `ab0928c`, `fb9602a`.
- DEV: `backend/src/modules/ocr/**`, `backend/src/workers/ocr_consumer.py`, `backend/alembic/versions/0004_create_recetas_ocr.py`, `backend/requirements.txt`, `backend/src/config.py`, `backend/src/main.py`, `backend/src/modules/carrito/models.py`, `backend/src/modules/pagos/**`, `frontend/src/**`, `informes/DEV-HU-06.md`; commit `e242b25`.
- El commit del DEV no modificó archivos de prueba (verificado con `git diff 41953e6..HEAD -- backend/tests frontend/tests`: solo las pruebas del TESTER).
- LEAD: contratos HU-06 v1 y HU-07 v2 (`41953e6`), veredicto.
- No se cometieron artefactos no rastreados (`frontend/dist`, `package.json` raíz, `package-lock.json`).
