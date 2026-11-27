# CONTRATO — HU-06 Automatización OCR de recetas médicas

**Tipo:** Feature
**Versión:** v1
**Estado:** Aprobado (2026-11-27, usuario humano)
**Origen:** `HUs/HU-06-automatizacion-ocr-recetas-medicas.md`

---

## Paquete de contexto

| Fuente | Por qué entra |
|---|---|
| `HUs/HU-06-automatizacion-ocr-recetas-medicas.md` | Historia, criterios y escenarios Gherkin. |
| `TECH-DESIGN.md` §OCR de receta (L103-108) | Endpoints 202/polling, umbral, fallback, worker 2 hilos. |
| `adrs/0008-ocr.md` | Tesseract, umbral 65%, fallback asistido, descarte parcial, polling 1.5s×15. |
| `adrs/0015-lpdp.md` | Retención mínima del documento (dato de salud) y minimización. |
| `adrs/0004-contratos-api.md` | Endpoints de job OCR y estados base. |
| `adrs/0007-broker-workers.md` | Cola `ocr.procesar`, worker en proceso dedicado, idempotencia. |
| `adrs/0003-modelo-datos.md` | `Receta/OCRJob` y asociación `receta_id` para autorizar `requiere_receta`. |
| `adrs/0012-erp.md` | Verificación atómica de stock (MVP local MySQL). |
| `contratos/CONTRATO-HU-05.md` | Carrito, reserva e inserción de ítems. |
| `contratos/CONTRATO-HU-07.md` | Checkout; HU-07 difirió a HU-06 el bloqueo por receta (W-03, decisión 8). |

## Interfaz observable

- API HTTP: `POST /api/v1/ocr/recetas` (subida), `GET /api/v1/ocr/jobs/{job_id}` (polling), `POST /api/v1/ocr/jobs/{job_id}/confirmar` (validación asistida).
- Bloqueo de checkout por receta en `POST /api/v1/checkout` (extiende HU-07).
- Pantalla con botón `Leer receta`: subida, polling, fallback asistido, alerta de quiebre y redirección al carrito.

## Comportamiento

### Sesión requerida

- El OCR exige **sesión autenticada** (dato de salud y el pago ya exige auth). Sin sesión → **HTTP 401**.
- Un job solo es visible para su dueño; ajeno o inexistente → **HTTP 404**.

### Subida de receta

**Entrada**

```http
POST /api/v1/ocr/recetas   (multipart/form-data, campo "archivo")
```

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| Camino feliz | Archivo JPG/PNG/PDF válido | HTTP 202; `{ job_id, estado:"procesando", poll_interval_ms:1500 }`. | ADR-0008 §5; ADR-0004 |
| Sin sesión | Sin token | HTTP 401. | **decisión propuesta** |
| Formato no soportado | Extensión/tipo inválido | HTTP 422; `"Formato de archivo no soportado. Usa JPG, PNG o PDF"`. | **decisión propuesta** |
| Archivo demasiado grande | > 10 MB | HTTP 413; `"El archivo supera el tamaño máximo permitido"`. | **decisión propuesta** |

- Un job procesa **un** archivo. El documento original se elimina tras el procesamiento (LPDP).

### Consulta del job (polling)

**Entrada**

```http
GET /api/v1/ocr/jobs/{job_id}
```

| Caso | Salida esperada | Origen |
|---|---|---|
| En proceso | HTTP 200; `{ estado:"procesando" }`. | ADR-0004 |
| Éxito con stock suficiente | HTTP 200; `{ estado:"completado", receta_id, items:[{ producto_id, nombre, cantidad }] }`. Los ítems ya están en el carrito. | ADR-0008 §3; HU-06 crit.4 |
| Baja confianza / producto no resuelto | HTTP 200; `{ estado:"requiere_validacion", items_sugeridos:[{ texto, producto_id?, cantidad, confianza }], confianza }`. | ADR-0008 §3 |
| Quiebre de stock (alguno faltante) | HTTP 200; `{ estado:"sin_stock", faltantes:[{ nombre, solicitado, disponible }], mensaje }`. No se insertó ningún ítem. | ADR-0008 §4; HU-06 crit.5 |
| Error técnico del motor | HTTP 200; `{ estado:"error", mensaje }`. | ADR-0004 |
| Job ajeno/inexistente | HTTP 404. | **decisión propuesta** |

El estado `sin_stock` **extiende** el enum base de ADR-0004 (`procesando`, `completado`, `requiere_validacion`, `error`).

### Validación asistida (fallback)

**Entrada**

```http
POST /api/v1/ocr/jobs/{job_id}/confirmar
Body: { items: [ { producto_id, cantidad } ] }
```

| Caso | Salida esperada | Origen |
|---|---|---|
| Confirmación válida con stock | HTTP 200; `{ estado:"completado", receta_id, items:[...] }`; ítems insertados. | ADR-0008 §3 |
| Confirmación con faltante | HTTP 409; `{ estado:"sin_stock", faltantes:[...], mensaje }`; sin inserción parcial. | ADR-0008 §4; PA-03 |
| Job no está en `requiere_validacion` | HTTP 409. | **decisión propuesta** |
| Sin sesión / job ajeno | HTTP 401 / 404. | **decisión propuesta** |

### Inserción, stock y autorización de receta

| Caso | Salida esperada | Origen |
|---|---|---|
| Todos los ítems con stock | Inserta **todos** con las cantidades prescritas, asocia `receta_id` al carrito y habilita el pago de productos `requiere_receta`. | HU-06 crit.4; ADR-0008 §3 |
| Al menos uno sin stock | Descarta la inserción parcial: **no** inserta ningún ítem y devuelve los faltantes con mensaje. | HU-06 crit.5; PA-03 |
| Mensaje por faltante | `"Lo sentimos, no contamos con stock disponible de {nombre} para completar su receta médica"`. | HU-06 esc.2/3 |
| Normalización de nombres/marcas | Contra el catálogo (Meilisearch si está disponible; si no, catálogo local/seed). | ADR-0008 §2; **decisión propuesta** (fallback sin Meilisearch) |

### Bloqueo de checkout por receta (W-03, ex-HU-07)

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| Carrito con `requiere_receta` sin receta validada | `POST /api/v1/checkout` | HTTP 409; `"Debes adjuntar y validar tu receta médica para continuar con el pago"`. | TECH-DESIGN L101; HU-07 decisión 8 |
| Carrito con `requiere_receta` cubierto por `receta_id` validada | `POST /api/v1/checkout` | Continúa el flujo normal de HU-07. | ADR-0008 §3 |
| Carrito sin productos `requiere_receta` | `POST /api/v1/checkout` | Sin cambios respecto a HU-07. | HU-07 |

### Privacidad y retención (LPDP)

- El documento original (imagen/PDF) se **elimina** tras el procesamiento; solo se conserva el resultado estructurado (ítems, cantidades, `receta_id`). | ADR-0015
- No se registran en logs datos de salud ni el contenido del documento. | AGENTS.md; ADR-0015

### Pantalla `Leer receta`

- Botón visible `Leer receta`; si no hay sesión, invita a iniciar sesión.
- Sube JPG/PNG/PDF; tras 202, sondea `GET /api/v1/ocr/jobs/{job_id}` cada 1.5 s (máx. 15 intentos). | ADR-0008 §5
- `completado` → redirige a `/carrito`. | HU-06 crit.4
- `requiere_validacion` → abre validación asistida (confirmar/ajustar antes de enviar al carrito). | ADR-0008 §3
- `sin_stock` → alerta con los faltantes; no redirige. | HU-06 crit.5
- `error` → mensaje de reintento. | **decisión propuesta**

## Nombres que no se negocian

| Tipo | Valor exacto |
|---|---|
| POST | `/api/v1/ocr/recetas` |
| GET | `/api/v1/ocr/jobs/{job_id}` |
| POST | `/api/v1/ocr/jobs/{job_id}/confirmar` |
| Campo subida | `archivo` (multipart/form-data) |
| Respuesta subida | `job_id`, `estado`, `poll_interval_ms` |
| Estados del job | `procesando`, `completado`, `requiere_validacion`, `sin_stock`, `error` |
| Campo resultado | `receta_id`, `items`, `items_sugeridos`, `faltantes`, `confianza`, `mensaje` |
| Umbral de confianza | `65%` |
| Polling | cada `1.5 s`, máx. `15` intentos |
| Formatos | `JPG`, `PNG`, `PDF` |
| Botón | `Leer receta` |
| Mensaje sin stock | `Lo sentimos, no contamos con stock disponible de {nombre} para completar su receta médica` |
| Mensaje bloqueo checkout | `Debes adjuntar y validar tu receta médica para continuar con el pago` |
| Mensaje formato | `Formato de archivo no soportado. Usa JPG, PNG o PDF` |
| Mensaje tamaño | `El archivo supera el tamaño máximo permitido` |
| Mensaje baja confianza | `No pudimos leer la receta con suficiente confianza. Revisa y confirma los medicamentos` |
| Mensaje error técnico | `No se pudo procesar la receta. Intenta nuevamente` |

## Rutas de cada rol

| Rol | Rutas | Origen |
|---|---|---|
| TESTER | `backend/tests/**`, `frontend/tests/**`, `frontend/src/**/*.test.tsx`, `frontend/src/**/*.spec.ts` | `AGENTS.md` |
| DEV | `backend/src/**`, `backend/alembic/**`, `backend/requirements*`, `backend/pyproject.toml`, `backend/.env.example`, `backend/web.config`, `frontend/src/**` (excepto tests), `frontend/package*.json`, `infra/**` | `AGENTS.md` |
| LEAD/humano | `contratos/**`, `informes/**`, `AGENTS.md`, `docs/**` | `AGENTS.md` |

## Avisos de contexto

- **Bloquea a HU-06 modificar `POST /api/v1/checkout`** para el bloqueo W-03 (diferido por HU-07, decisión 8). Se bump a v2 de `CONTRATO-HU-07.md` al aprobar este contrato.
- **Tesseract no está instalado** y **Meilisearch no corre**. Decisiones: Tesseract real en producción con **proveedor OCR inyectable**; en pruebas el job se resuelve de forma determinista **en proceso** (sin worker externo ni dependencia de la precisión real). La normalización cae a catálogo local/seed si no hay Meilisearch.
- El **worker** (`src/workers/main.py`) es un esqueleto; HU-06 agrega el consumidor `ocr.procesar` (ADR-0007) con concurrencia 2, pero las pruebas no deben exigir un proceso externo.
- Tesseract procesa en `asyncio.to_thread` (máx. 2 hilos); no bloquea el event loop (S-04).
- El OCR es **solo autenticado**; el guest debe iniciar sesión antes de `Leer receta`.
- Se necesita migración nueva para `Receta/OCRJob` (y su `receta_id`) y posiblemente columnas de autorización en carrito.
- Nunca loguear ni persistir el documento tras procesarlo (LPDP).

## Decisiones propuestas (no venían en la tarea)

| # | Decisión | Por qué hace falta | Estado |
|---|---|---|---|
| 1 | Endpoints, campos y mensajes de §Nombres | La HU no fija contratos ni textos de error. | Aprobada por humano (2026-11-27) |
| 2 | Estado `sin_stock` (extiende ADR-0004) | Representa quiebre de stock sin insertar parcial. | Aprobada por humano (2026-11-27) |
| 3 | OCR solo autenticado (401 sin sesión) | Dato de salud y el pago exige auth; decisión humana 2026-11-27. | Aprobada por humano (2026-11-27) |
| 4 | Tesseract real + proveedor inyectable con resolución determinista en pruebas | Tesseract no instalado; evita pruebas frágiles por precisión OCR. | Aprobada por humano (2026-11-27) |
| 5 | Normalización con fallback a catálogo local/seed si no hay Meilisearch | Meilisearch no corre en el entorno. | Aprobada por humano (2026-11-27) |
| 6 | Un archivo por job, ≤ 10 MB, JPG/PNG/PDF | La HU no fija límites. | Aprobada por humano (2026-11-27) |
| 7 | Bloqueo de checkout W-03 con el mensaje indicado | HU-07 lo difirió; decisión humana 2026-11-27. | Aprobada por humano (2026-11-27) |
| 8 | Eliminar el documento original tras procesarlo; conservar solo el resultado estructurado | Retención mínima LPDP. | Aprobada por humano (2026-11-27) |

## Fuera del contrato (decide el DEV)

- Implementación del motor OCR y del proveedor inyectable; detalles de Tesseract y preprocesado de imagen/PDF.
- Estructura interna de `Receta/OCRJob`, cola `ocr.procesar`, worker y migración Alembic.
- Estrategia de normalización (fuzzy) y de asociación texto→producto.
- Almacenamiento temporal del archivo y su borrado.
- Estilos visuales más allá de textos, botones y flujo fijados.

## Preguntas abiertas para el humano

Ninguna. Decisiones 3, 4 y 7 aprobadas por el usuario humano (2026-11-27); el resto se aprueba con el contrato.

## Changelog

| Versión | Fecha | Cambio | Motivo | Aprobado por |
|---|---|---|---|---|
| v1 | 2026-11-27 | Versión inicial; OCR solo autenticado, Tesseract+stub, bloqueo W-03 | Inicio de HU-06 y respuestas del humano | Usuario humano |
