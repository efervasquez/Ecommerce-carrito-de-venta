# Informe de Entrega DEV — HU-03 Catálogo y búsqueda difusa

**Fecha:** 2026-11-23  
**Rol:** DEV  
**Documento base:** `contratos/CONTRATO-HU-03.md` (v1, aprobada 2026-11-23)  
**Tipo de tarea:** Feature  
**Rama:** `feat/hu-03-catalogo`

## 1. Qué se construyó

### Backend

- Nuevo módulo `backend/src/modules/catalogo/` separado por capas de lectura:
  - `router.py`: `GET /api/v1/catalogo/buscar`.
  - `service.py`: orquestación CQRS y mapeo de errores.
  - `repository.py`: lectura principal desde Meilisearch mediante API REST asíncrona.
  - `schemas.py`: respuesta tipada con `items`, `next_cursor` y `has_next` y los campos exactos
    de producto.
- Búsqueda por `nombre` y `componentes`, typo tolerance de Meilisearch, filtro de stock positivo,
  cursor opaco y `limit` validado entre 1 y 50.
- Fallback local configurable (`CATALOG_SEED_FALLBACK=true`) para desarrollo verificable cuando
  Meilisearch no está levantado; usa el mismo contrato y ranking difuso básico para el seed local.
- Rate limit de catálogo de 20 consultas por segundo/IP en `GET /api/v1/catalogo/buscar`.
- Configuración nueva: `MEILISEARCH_URL`, `MEILISEARCH_API_KEY`, `MEILISEARCH_INDEX` y
  `CATALOG_SEED_FALLBACK`.
- Seed reproducible en `infra/catalogo-seed.json` y script PowerShell
  `infra/seed-meilisearch.ps1` que configura atributos de búsqueda/filtros y carga documentos.
- No se agregaron tablas ni escrituras de catálogo: la implementación permanece en el lado de
  lecturas CQRS; las escrituras y carrito persistente quedan fuera de HU-03/HU-05.

### Frontend

- Nueva ruta `/catalogo` con TanStack Query `useInfiniteQuery`, cursor incremental y sin paginación
  numérica.
- Virtualización con `@tanstack/react-virtual`, carga al aproximarse al final, estados visibles de
  carga, error y sin resultados.
- Tarjetas accesibles con fotografía/placeholder, nombre, componentes, precio en PEN, descuento
  solo cuando aplica, alerta exacta de stock bajo, etiqueta `Precios bajos`, indicador de receta y
  botón `Agregar al carrito`.
- Contador local/temporal de carrito; no persiste ni reserva stock.
- Enlace `Explorar catálogo` desde la vista principal.

## 2. Cómo se prueba a mano

### Meilisearch

```powershell
# Levantar Meilisearch local en http://127.0.0.1:7700
cd C:\Temp2\Ecommerce-carrito-de-venta
.\infra\seed-meilisearch.ps1
```

Variables opcionales: `MEILISEARCH_URL`, `MEILISEARCH_API_KEY`, `MEILISEARCH_INDEX`.

### Backend

```powershell
cd backend
.\.venv\Scripts\uvicorn src.main:app --port 8000 --reload
```

Ejemplo:

```powershell
curl "http://localhost:8000/api/v1/catalogo/buscar?q=ibuprofno%20400&limit=2"
```

La consulta devuelve `Ibuprofeno 400mg`. La respuesta siguiente se solicita con el valor de
`next_cursor`; `q` vacío devuelve el catálogo inicial. El endpoint responde 422 si `limit` falta,
es menor que 1 o supera 50 y 429 al superar 20 consultas por segundo/IP.

### Frontend

```powershell
cd frontend
npm run build
npm run dev
```

Abrir `http://localhost:5173/catalogo`, buscar `ibuprofno 400`, desplazarse hasta el final y usar
`Agregar al carrito`. El contador es temporal y se reinicia al recargar.

## 3. Verificación realizada

- `python -m compileall -q src`: correcto.
- OpenAPI expone `/api/v1/catalogo/buscar`.
- Verificación HTTP manual con fallback local: typo 200 con producto esperado, primera página y
  cursor incremental sin duplicados, consulta sin resultados 200 vacío y `limit=0` 422.
- `npm run build`: TypeScript y Vite correctos.
- `frontend/dist` fue eliminado después del build.

## 4. Rutas tocadas

- `backend/src/**`, `backend/requirements.txt`, `backend/.env.example`
- `frontend/src/**`, `frontend/package.json`, `frontend/package-lock.json`
- `infra/catalogo-seed.json`, `infra/seed-meilisearch.ps1`
- `informes/DEV-HU-03.md`

No se tocaron `backend/tests/**`, `frontend/tests/**`, archivos de paquete de la raíz ni
`frontend/dist`.
