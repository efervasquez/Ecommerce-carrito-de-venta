# Informe de Entrega DEV — HU-06 Automatización OCR de recetas

**Fecha:** 2026-11-27  
**Rol:** DEV  
**Documento base:** `contratos/CONTRATO-HU-06.md` v1 y `CONTRATO-HU-07.md` v2 (W-03)  
**Rama:** `feat/hu-06-ocr`  
**Coordinación:** marcadores `receta_ok`, `receta_lowconf`, `receta_nostock` y `receta_error`.

## 1. Backend

### Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/ocr/recetas` | Multipart `archivo` (auth), 202 con `job_id`, `estado:"procesando"`, `poll_interval_ms:1500`. |
| GET | `/api/v1/ocr/jobs/{job_id}` | `procesando`, `completado`, `requiere_validacion`, `sin_stock`, `error`; 404 ajeno/inexistente. |
| POST | `/api/v1/ocr/jobs/{job_id}/confirmar` | Validación asistida; 200 completado, 409 sin_stock / estado inválido. |

- Formato JPG/PNG/PDF → 422 con el mensaje exacto; >10 MB → 413 con el mensaje exacto.
- Sin sesión → 401. Los jobs ajenos/inexistentes → 404.
- Normalización contra catálogo con fallback a seed (Meilisearch no corre), umbral 65%.
- Inserción **atómica** de toda la receta al carrito; si falta stock no se inserta nada (PA-03) y se
  devuelve el mensaje exacto por faltante.
- La receta validada asocia `receta_id` al carrito y habilita productos `requiere_receta`.
- W-03: `POST /api/v1/checkout` responde 409 con
  `Debes adjuntar y validar tu receta médica para continuar con el pago` si el carrito contiene
  productos con receta sin receta validada. Con receta validada continúa HU-07 con normalidad.

### Modelos y migración

- `0004_create_recetas_ocr.py`: tabla `recetas` (job OCR + resultado estructurado),
  `carritos.receta_id`, `pedidos.receta_id` y `auditoria_receta_pendiente`.
- El documento original **nunca se persiste**: se mantiene en memoria solo durante el procesamiento
  y se descarta en `finally`; en la fila se guarda solo el resultado estructurado (LPDP).
- No se registran en logs datos de salud ni contenido del documento.

### Proveedor OCR y worker

- `OCRProvider` inyectable. `FakeOCRProvider` en `APP_ENV=test`/`OCR_TEST_MODE` (y bajo pytest, cuyo
  fixture fija `APP_ENV=test` después de cachear settings) decide por marcador:
  - `receta_ok.*` → dos productos del catálogo con stock.
  - `receta_lowconf.*` → confianza 0.42 → `requiere_validacion`.
  - `receta_nostock.*` → un faltante sin stock → `sin_stock` sin inserción parcial.
  - `receta_error.*` → fallo técnico → `error` con mensaje exacto.
- `TesseractOCRProvider` para producción: `pytesseract` + `Pillow` (imágenes) y `pypdf` (PDF),
  ejecutado en `asyncio.to_thread` con semáforo de 2 hilos (ADR-0008 S-04). Lee `TESSERACT_CMD`
  desde configuración (placeholder en `.env.example`).
- **Tesseract no está instalado en este entorno**: por diseño el proveedor cae al fake cuando el
  binario no existe, así que las pruebas no dependen de precisión OCR ni de binarios externos. Para
  producción basta instalar Tesseract en el servidor Windows y definir `TESSERACT_CMD`.
- Cola `ocr.procesar` con consumidor en `src/workers/ocr_consumer.py` (prefetch 2, concurrencia 2),
  iniciado desde `src/workers/main.py` cuando `OCR_WORKER_ENABLED=true`. En pruebas el job se
  resuelve en proceso de forma determinista, sin worker externo.

### Dependencias

`backend/requirements.txt`: `python-multipart>=0.0.9`, `Pillow>=10.3.0`,
`pytesseract>=0.3.10`, `pypdf>=4.2.0`. Multipart se parsea de forma nativa en el endpoint, así que
las pruebas corren aunque dichos paquetes aún no estén instalados en el venv local.

## 2. Frontend

- Botón `Leer receta` en `/carrito` y pantalla `/receta`; invitación a iniciar sesión si es guest.
- Subida JPG/PNG/PDF, polling cada 1.5 s (máx. 15), redirección a `/carrito` en `completado`,
  modal de validación asistida para `requiere_validacion`, alerta con faltantes para `sin_stock` y
  mensaje de reintento para `error`.
- `src/services/ocr.ts` y `src/components/LeerReceta.tsx`.

## 3. Verificación

```powershell
cd backend
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python.exe -m pytest tests/test_hu06_ocr_recetas.py -q
```

- HU-06: **17 passed, 1 skipped** (skip LPDP no observable en caja negra).
- Regresión HU-05 + HU-07: **38 passed, 5 skipped**.

```powershell
cd frontend
npm test            # 12 archivos, 46 passed
npm run build       # OK
```

## 4. Rutas tocadas

- `backend/alembic/versions/0004_create_recetas_ocr.py`, `backend/src/modules/ocr/**`
- `backend/src/modules/carrito/models.py`, `backend/src/modules/pagos/models.py`,
  `backend/src/modules/pagos/service.py` (W-03), `backend/src/main.py`, `backend/src/config.py`,
  `backend/.env.example`, `backend/requirements.txt`, `backend/src/workers/**`
- `frontend/src/services/ocr.ts`, `frontend/src/components/LeerReceta.tsx`,
  `frontend/src/pages/{Receta,OcrReceta}.tsx`, `frontend/src/pages/Carrito.tsx`, `frontend/src/App.tsx`
- `informes/DEV-HU-06.md`

No se tocaron tests ni `contratos/**`.
