# Technical Design Document: Plataforma E-commerce — Botica la Luz

**Tipo de proyecto:** Greenfield
**Design.md disponible:** No — el modelo de datos se derivó solo del PRD.

## Resumen

Se construye una web app responsive (PWA/React) para digitalizar la venta de Botica la Luz: carrito
con reserva de stock, catálogo con búsqueda difusa y scroll infinito, autoregistro por email,
lectura de recetas por OCR, pasarela de pagos Stripe (test), buzón de despacho con ciclo de vida de
pedido, flujo de reclamos sin reembolso y módulo de contingencia manual de stock. El despliegue es
on-premise (Windows 11 Pro + IIS 10 + MySQL) sin costos de licencia, según el PRD y `AGENTS.md`.

## Arquitectura de componentes

- **frontend/** — React 18 + Vite (S.P.A. responsive). TanStack Query (estado de servidor) + Zustand
  (estado de cliente). Habla con el backend solo por REST `/api/v1`.
- **backend/** — FastAPI (Python 3.12) monolito modular por capas
  (`Handler/Route -> Controller -> Service -> Repository`), módulos: auth, catálogo, carrito,
  pedidos, OCR, despacho, reclamos, stock.
- **workers/** — consumidores async/await del bus de eventos (despacho, OCR, correos, purga) en el
  mismo código.
- **infra/** — RabbitMQ (bus de eventos), Meilisearch (índice de búsqueda), MySQL (única fuente de
  verdad), Tesseract (OCR), IIS 10 (servidor web), Tareas programadas de Windows (purga de carritos).

```
[ React/Vite ] --REST--> [ FastAPI monolito modular ] --SQL--> [ MySQL ]
                              |   (CQRS catálogo)        ^
                              |---índice de lectura------>| [ Meilisearch ]
                              |--eventos--> [ RabbitMQ ] --> [ workers async ]
                              [ Tesseract OCR ] (worker, dato de salud retención mínima)
```

## Decisiones de arquitectura

| # | Decisión | Estado |
|---|---|---|
| [ADR-0001](adrs/0001-componentes.md) | Monolito modular + workers | Aceptado |
| [ADR-0002](adrs/0002-stack-base.md) | Stack base FastAPI + React/Vite + MySQL + IIS on-premise | Aceptado |
| [ADR-0003](adrs/0003-modelo-datos.md) | Modelo de datos (entidades, categorías, carrito guest) | Aceptado |
| [ADR-0004](adrs/0004-contratos-api.md) | REST + OpenAPI + JWT/RBAC | Aceptado |
| [ADR-0005](adrs/0005-cqrs-catalogo.md) | CQRS para el catálogo | Aceptado |
| [ADR-0006](adrs/0006-busqueda-fuzzy.md) | Búsqueda difusa con Meilisearch | Aceptado |
| [ADR-0007](adrs/0007-broker-workers.md) | Bus de eventos y workers con RabbitMQ | Aceptado |
| [ADR-0008](adrs/0008-ocr.md) | OCR con Tesseract | Aceptado |
| [ADR-0009](adrs/0009-sesion-cache.md) | Sesión/carrito/cache MySQL-only | Aceptado |
| [ADR-0010](adrs/0010-estado-frontend.md) | Estado frontend con TanStack Query + Zustand | Aceptado |
| [ADR-0011](adrs/0011-reserva-stock.md) | Reserva de stock al agregar + TTL + purga | Aceptado |
| [ADR-0012](adrs/0012-erp.md) | Integración ERP post-MVP | Aceptado |
| [ADR-0013](adrs/0013-consistencia-pago.md) | Consistencia pago/stock con transacciones nativas | Aceptado |
| [ADR-0014](adrs/0014-disponibilidad.md) | Disponibilidad single-node + riesgo | Aceptado |
| [ADR-0015](adrs/0015-lpdp.md) | Cumplimiento LPDP (minimización + cifrado) | Aceptado |

## Modelo de datos

Entidades principales (ver ADR 0003): `Usuario` (RBAC), `Categoria`, `Producto` (atributos
comerciales y clínicos), `Stock` (disponible/reservado), `Sesion`, `Carrito`/`CarritoItem`,
`Pedido` (estados Registrado → Preparando producto → En camino → Entregado), `Pago` (Stripe test),
`Receta`/`OCRJob`, `Reclamo` (máx. 3 intentos), `Despacho` (rutas por zona + motorizado).

## Criterios de aceptación por flujo

### Autoregistro y recuperación de contraseña
- [ ] Al ingresar solo un email válido y no registrado, se crea la cuenta y se envía una contraseña provisional por SMTP (con confirmación de envío y reintento).
- [ ] Un email ya registrado no crea cuenta duplicada y responde sin filtrar si el email existía.
- [ ] El link de recuperación es de un solo uso, expira, y fuerza un formulario de nueva contraseña antes de reingresar.
- [ ] Ninguna respuesta loguea la contraseña ni el token (correlación de trazabilidad solo por `correlation_id`).

### Búsqueda fuzzy y detalle de producto
- [ ] "camiaa" devuelve productos con "camisa" (tolerancia a typos) en <2.5 s bajo 250 usuarios.
- [ ] El listado es scroll infinito sin paginación; la tarjeta muestra foto, nombre, componentes, precio, oferta %, alerta de stock <6, etiqueta "Precios bajos" y botón "Agregar al carrito".
- [ ] El detalle muestra foto, componentes, precio, flag de receta, presentación, métodos de entrega, contraindicaciones, precauciones y reacciones adversas.

### Carrito con reserva y ofertas prioritarias
- [ ] Agregar al carrito decrementa stock disponible (reserva) de forma transaccional; stock <6 dispara la alerta visual.
- [ ] Los productos con oferta activa aparecen siempre en la sección superior del carrito.
- [ ] Al vencer el TTL de reserva, el job programado libera el stock y purga el carrito (PA-01 pendiente: duración).

### OCR de receta
- [ ] Al adjuntar foto/PDF, se extraen componentes/marcas y cantidades y se cruzan con stock.
- [ ] Con stock completo, se añaden los ítems y se redirige al carrito.
- [ ] Ante quiebre de stock, se detiene la inserción y se alerta el medicamento faltante (PA-03 pendiente: comportamiento con stock mixto).
- [ ] El documento de receta se trata como dato de salud con retención mínima (ADR 0015).

### Checkout y pago
- [ ] El pago Stripe (test) confirma/libera stock en una única transacción MySQL con clave de idempotencia.
- [ ] Un webhook reintentado no produce doble cargo ni doble decremento de stock.
- [ ] No existe ninguna opción de reembolso en las interfaces de cliente ni administrador (RF-04.2).

### Buzón de despacho
- [ ] Las órdenes confirmadas se consolidan y agrupan rutas por cercanía de zona.
- [ ] La asignación a motorizado es por orden de llegada o auto-asignación manual.
- [ ] El pedido transita solo por los 4 estados: Registrado, Preparando producto, En camino, Entregado.

### Reclamos
- [ ] El reclamo exige foto del producto dañado y comprobante de pago.
- [ ] Se permiten hasta 3 intentos adicionales de cambio en campo antes de escalar/cerrar (RF-04.3).

### Contingencia de stock manual
- [ ] El backoffice permite alta y edición total de producto (todos los campos del PRD) y actualización directa de stock.

## Riesgos técnicos abiertos

- **PA-01 (reserva):** duración exacta del TTL de reserva y regla de liberación — parametriza ADR 0011; a definir con PM/BA.
- **PA-03 (OCR mixto):** comportamiento con recetas que mezclan medicamentos con y sin stock — afecta el flujo OCR.
- **PA-04 (reclamos):** si el flujo de reclamos es un estado más del ciclo de vida o un sub-flujo independiente — afecta el modelo de `Pedido`/`Reclamo`.
- **PA-05 (reportería):** la "matriz de reportería del Backoffice" mencionada en el changelog no está en el alcance — decidir si se incorpora como RF.
- **Disponibilidad 99.5% en un solo nodo** (ADR 0014): el KPI queda expuesto a punto único de fallo; revisar con PM.
- **Precisión de OCR manuscrito** (ADR 0008): requiere validación humana ante baja confianza.
