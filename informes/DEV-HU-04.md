# Informe de Entrega DEV — HU-04 Detalle extendido del producto

**Fecha:** 2026-11-23  
**Rol:** DEV  
**Documento base:** `contratos/CONTRATO-HU-04.md` (v1, aprobada 2026-11-23)  
**Tipo de tarea:** Feature  
**Rama:** `feat/hu-04-detalle-producto`

## 1. Qué se construyó

### Backend

- `GET /api/v1/catalogo/productos/{producto_id}` integrado en el módulo de lecturas CQRS de
  `catalogo`.
- Payload completo: `id`, `nombre`, `imagen_url`, `componentes`, `precio_regular`, `moneda`,
  `descuento_porcentaje`, `requiere_receta`, `detalle`, `presentacion`, `metodos_entrega`,
  `contraindicaciones`, `precauciones_advertencias`, `reacciones_adversas`, `precios_bajos` y
  `stock_disponible`.
- Producto inexistente: HTTP 404 `Producto no encontrado.`.
- ID no numérico: HTTP 422 con parámetro inválido.
- Lectura principal desde documento Meilisearch; fallback local al seed cuando el servicio no está
  disponible, sin agregar escrituras ni tablas nuevas.
- Seed extendido con datos comerciales, clínicos y logísticos para los productos locales.

### Frontend

- Las tarjetas de `/catalogo` enlazan el nombre del producto a `/catalogo/productos/{id}`.
- Nueva pantalla de detalle con imagen/placeholder, precio, descuento condicional, receta,
  presentación, detalle, modalidades de entrega, precios bajos y secciones clínicas exactas:
  `Contraindicaciones`, `Precauciones/Advertencias` y `Reacciones adversas`.
- Selector entero de cantidad con validación de mínimo 1 y máximo `stock_disponible`.
- Producto sin stock deshabilita `Agregar al carrito`; cantidad inválida o superior al stock muestra
  error y no agrega.
- Agregado al carrito únicamente en contador local/temporal; no hay persistencia ni reservas.

## 2. Verificación manual

```powershell
cd backend
.\.venv\Scripts\python.exe -m compileall -q src
```

Con fallback local y Meilisearch apagado:

- `GET /api/v1/catalogo/productos/1` → HTTP 200 con todos los campos de detalle.
- `GET /api/v1/catalogo/productos/9999` → HTTP 404.
- `GET /api/v1/catalogo/productos/no-es-id` → HTTP 422.
- Seed JSON validado correctamente.

Frontend:

```powershell
cd frontend
npm run build
```

Resultado: TypeScript y Vite compilan correctamente. No se modifica ni se incluye `frontend/dist`.

## 3. Rutas tocadas

- `backend/src/modules/catalogo/{repository,router,schemas,service}.py`
- `backend/src/main.py`
- `infra/catalogo-seed.json`
- `frontend/src/services/catalog.ts`
- `frontend/src/pages/Catalogo.tsx`
- `frontend/src/pages/DetalleProducto.tsx`
- `frontend/src/App.tsx`
- `informes/DEV-HU-04.md`

No se tocaron `backend/tests/**`, `frontend/tests/**`, archivos `package.json`/`package-lock.json`
de la raíz ni se implementó carrito persistente/reserva de stock.
