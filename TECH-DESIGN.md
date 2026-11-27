# Technical Design Document: Plataforma E-commerce — Botica la Luz

**Tipo de proyecto:** Greenfield
**Design.md disponible:** No — el modelo de datos se derivó solo del PRD.

## Resumen

Se construye una web app responsive (PWA/React) para digitalizar la venta de Botica la Luz: carrito
con reserva de stock y prórroga en checkout, catálogo con búsqueda difusa y scroll infinito virtualizado,
autoregistro por email con activación segura y cooldown anti-spam, lectura de recetas por OCR con polling controlado,
pasarela de pagos Stripe (test) con CSP habilitada y salvaguarda de contingencia, buzón de despacho con ciclo de
vida de pedido y auditoría farmacéutica, flujo de reclamos con logística inversa integrada y módulo de contingencia
manual de stock. El despliegue es on-premise (Windows 11 Pro + IIS 10 + MySQL) sin costos de licencia, según el PRD
y `AGENTS.md`.

## Arquitectura de componentes

- **frontend/** — React 18 + Vite (S.P.A. responsive con virtual scrolling `@tanstack/react-virtual`, ADR 0010).
  TanStack Query (estado de servidor) + Zustand (estado de cliente). Habla con el backend solo por REST `/api/v1`.
- **backend/** — FastAPI (Python 3.12) monolito modular por capas
  (`Handler/Route -> Controller -> Service -> Repository`), módulos: auth, catálogo, carrito,
  pedidos, OCR, despacho, reclamos, stock. Alojado en IIS 10 bajo `HttpPlatformHandler` atendiendo tráfico HTTP.
- **workers/** — consumidores async/await de RabbitMQ ejecutados como **Servicio de Windows supervisado 24/7 (vía NSSM)**
  en el mismo repositorio (`python -m src.workers.main`, ADR 0001, ADR 0007), desacoplados del ciclo de vida HTTP de IIS.
- **infra/** — RabbitMQ (bus de eventos con colas separadas `email.critico` vs `email.auth`, DLQ y QoS prefetch, ADR 0007),
  Meilisearch (índice de búsqueda difusa, ADR 0006), MySQL (única fuente de verdad, TDE InnoDB, ADR 0015),
  Tesseract (OCR en worker con ThreadPoolExecutor, ADR 0008), IIS 10 (servidor web con CSP habilitada para Stripe y rate limiting, ADR 0019),
  Brevo / SendGrid relay (correo transaccional con cuota de 300 mails/día, ADR 0018), Tareas programadas de Windows (purga de carritos y tokens).

```
[ React/Vite ] --REST /api/v1--> [ IIS 10 / FastAPI HTTP ] --SQL--> [ MySQL ]
                                         |   (CQRS catálogo)           ^
                                         |---índice de lectura-------->| [ Meilisearch ]
                                         |--eventos--> [ RabbitMQ ]    |
                                                            |          |
                                  [ Servicio Windows NSSM: Workers ] --|
                                  (OCR Tesseract, Brevo Email, Despacho)
```

## Decisiones de arquitectura

| # | Decisión | Estado |
|---|---|---|
| [ADR-0001](adrs/0001-componentes.md) | Monolito modular + workers como servicio Windows (NSSM) | Aceptado |
| [ADR-0002](adrs/0002-stack-base.md) | Stack base FastAPI + React/Vite + MySQL + IIS on-premise | Aceptado |
| [ADR-0003](adrs/0003-modelo-datos.md) | Modelo de datos (entidades, categorías, auditoría recetas, reposición) | Aceptado |
| [ADR-0004](adrs/0004-contratos-api.md) | REST + OpenAPI + JWT/RBAC + Jobs asíncronos y health check | Aceptado |
| [ADR-0005](adrs/0005-cqrs-catalogo.md) | CQRS para el catálogo (alternativas evaluadas) | Aceptado |
| [ADR-0006](adrs/0006-busqueda-fuzzy.md) | Búsqueda difusa con Meilisearch y sincronización por eventos | Aceptado |
| [ADR-0007](adrs/0007-broker-workers.md) | Bus de eventos RabbitMQ (NSSM, colas separadas, QoS) | Aceptado |
| [ADR-0008](adrs/0008-ocr.md) | OCR con Tesseract (fallback manual y contrato polling) | Aceptado |
| [ADR-0009](adrs/0009-sesion-cache.md) | Sesión/carrito/cache MySQL-only (cookies HttpOnly) | Aceptado |
| [ADR-0010](adrs/0010-estado-frontend.md) | Estado frontend (TanStack Query + Zustand + virtual scrolling) | Aceptado |
| [ADR-0011](adrs/0011-reserva-stock.md) | Reserva de stock + prórroga checkout (`en_pago`) + purga | Aceptado |
| [ADR-0012](adrs/0012-erp.md) | Integración ERP post-MVP (protocolo por lotes y tx_context) | Aceptado |
| [ADR-0013](adrs/0013-consistencia-pago.md) | Checkout en dos fases (prórroga reserva y salvaguarda contingencia) | Aceptado |
| [ADR-0014](adrs/0014-disponibilidad.md) | Disponibilidad single-node + riesgo | Aceptado |
| [ADR-0015](adrs/0015-lpdp.md) | Cumplimiento LPDP (minimización + TDE InnoDB) | Aceptado |
| [ADR-0016](adrs/0016-anti-abuso-carrito-guest.md) | Anti-abuso carrito guest (límites SKU + techo reservas por IP) | Aceptado |
| [ADR-0017](adrs/0017-tokens-seguridad.md) | Tokens de seguridad (activación + recuperación con cooldown) | Aceptado |
| [ADR-0018](adrs/0018-transporte-smtp.md) | Transporte de correo (Brevo 300 mails/día + colas separadas) | Aceptado |
| [ADR-0019](adrs/0019-seguridad-perimetral-iis.md) | Seguridad perimetral en IIS 10 (CSP Stripe + URL Rewrite contextual) | Aceptado |

## Modelo de datos

Entidades principales (ver ADR 0003):
- `Usuario` (RBAC: cliente, motorizado, admin/farmacéutico/operador; estado `pendiente_activacion`, `activo`, `suspendido`).
- `Token` (activación y recuperación, hash SHA-256 + tipo + expiración + cooldown anti-spam, ADR 0017).
- `Categoria` y `Producto` (atributos comerciales y clínicos, flag `requiere_receta`).
- `Stock` (disponible y reservado por producto).
- `Sesion` (cookie `HttpOnly; SameSite=Lax; Secure`) y `Carrito`/`CarritoItem` (límites anti-abuso y techo por IP, ADR 0016).
- `Zona` (catálogo geográfico) y `Direccion` (cliente + zona).
- `Pedido` (tipo `venta`/`reposicion`, estado `Registrado` → `Preparando producto` → `En camino` → `Entregado` o `incidencia_stock`; flag `auditoria_receta_pendiente`, `receta_id`, `reclamo_id`, `despacho_id`).
- `Despacho` (rutas de consolidación 1:N pedidos por zona asignadas a motorizado).
- `Pago` (Stripe test, clave de idempotencia, checkout en 2 fases con prórroga, ADR 0013).
- `Receta`/`OCRJob` (con fallback asistido de baja confianza y contrato de polling, ADR 0008).
- `Reclamo` (pedido_origen_id, fotos, comprobante, máx. 3 intentos en campo, genera Pedido de reposición con baja contable por merma averiada).

## Criterios de aceptación por flujo

### Autoregistro y recuperación de contraseña
- [ ] Al ingresar solo un email válido y no registrado, se crea la cuenta con estado `pendiente_activacion` y se envía un link de activación por correo (Brevo/SendGrid, ADR 0018) con token opaco de un solo uso (ADR 0017).
- [ ] Al hacer clic en el link de activación, el usuario accede a un formulario para crear su propia contraseña; el token se invalida tras el uso.
- [ ] Un email ya registrado no crea cuenta duplicada y responde con el mismo HTTP 200 y mismo timing que un email no registrado (anti-enumeración).
- [ ] El link de recuperación es de un solo uso, expira en 1 hora, invalida tokens anteriores y fuerza nueva contraseña.
- [ ] Cooldown estricto: máximo 1 correo cada 15 minutos por email y máx. 3 solicitudes al día (ADR 0017).
- [ ] Rate limiting perimetral en IIS de máximo 3 req/min por IP en endpoints de auth (ADR 0019).
- [ ] Ninguna respuesta loguea la contraseña ni el token (correlación de trazabilidad solo por `correlation_id`).

### Búsqueda fuzzy y catálogo
- [ ] "camiaa" devuelve productos con "camisa" (tolerancia a typos) en <2.5 s bajo 250 usuarios vía Meilisearch.
- [ ] El listado es scroll infinito sin paginación implementado con virtualización de DOM (`@tanstack/react-virtual`, ADR 0010); la tarjeta muestra foto, nombre, componentes, precio, oferta %, alerta de stock <6, etiqueta "Precios bajos", indicador de receta y botón "Agregar al carrito".
- [ ] Búsquedas médicas con guiones o punto y coma (ej. "Vitamina C - 500mg") no son interceptadas por el URL Rewrite de IIS (W-06, ADR 0019).
- [ ] El detalle muestra foto, componentes, precio, flag de receta, presentación, métodos de entrega, contraindicaciones, precauciones y reacciones adversas.

### Carrito con reserva y control de recetas
- [ ] Agregar al carrito decrementa stock disponible (reserva) de forma transaccional; stock <6 dispara la alerta visual.
- [ ] Carritos guest tienen límite de 3 unidades/SKU y 10 productos distintos; rate limit de 1 req/s con burst de 5 y techo de 1 sesión guest activa / máx. 15 unidades por IP (ADR 0016).
- [ ] Los productos con oferta activa aparecen siempre en la sección superior del carrito.
- [ ] Al vencer el TTL de reserva (24 horas), el job programado libera el stock y purga el carrito (PA-01).
- [ ] Si el carrito contiene productos con `requiere_receta = true`, el checkout bloquea el pago hasta que el usuario adjunte su receta médica (vía OCR o subida de documento, W-03).

### OCR de receta
- [ ] Endpoint `POST /api/v1/ocr/recetas` responde `HTTP 202 Accepted` con `job_id` y tiempo sugerido de sondeo (W-04, ADR 0004).
- [ ] Frontend sondea `GET /api/v1/ocr/jobs/{job_id}` cada 1.5 s (máx. 15 intentos).
- [ ] Extracción ≥65% de confianza con stock disponible inserta automáticamente los ítems al carrito, asocia el `receta_id` y redirige a `/carrito` (RF-03.1).
- [ ] Ante quiebre de stock o confianza <65%, se activa la interfaz de fallback asistido para validación y ajuste manual del cliente (ADR 0008).
- [ ] El documento de receta se procesa en worker supervisado (2 hilos máx.) y se trata como dato de salud con retención mínima (ADR 0015).

### Checkout y pago
- [ ] Al solicitar `POST /api/v1/checkout`, el carrito pasa a `en_pago` y se le otorga una prórroga temporal de 10 minutos a la reserva, bloqueando la purga prematura mientras se interactúa con Stripe (C-02, ADR 0011, ADR 0013).
- [ ] La cabecera CSP en IIS autoriza explícitamente `https://js.stripe.com`, `https://hooks.stripe.com` y `https://api.stripe.com` (C-01, ADR 0019).
- [ ] El webhook `payment_intent.succeeded` confirma el pago y ejecuta `confirm_deduction_batch` dentro de una transacción MySQL atómica (<100ms) con clave de idempotencia (ADR 0012, ADR 0013).
- [ ] Si ocurre una discrepancia física imprevista en almacén al confirmar, el pedido se crea en estado `incidencia_stock` para abastecimiento prioritario por el farmacéutico de guardia (Opción B, C-02), preservando la regla comercial de no reembolso (RF-04.2).

### Buzón de despacho
- [ ] Las órdenes confirmadas se consolidan y agrupan rutas por cercanía de zona (1:N hacia `Despacho`).
- [ ] Si un pedido contiene productos bajo receta, requiere visto bueno en panel del farmacéutico (`auditoria_receta_pendiente = false`) antes de transicionar a `Preparando producto` (W-03).
- [ ] La asignación a motorizado es por orden de llegada o auto-asignación manual.
- [ ] El pedido transita por: `Registrado` → `Preparando producto` → `En camino` → `Entregado`.

### Logística inversa de Reclamos
- [ ] El reclamo exige foto del producto dañado y comprobante de pago.
- [ ] Al aprobarse, genera un `Pedido` de reposición (total 0.00) que reserva stock de reemplazo y se consolida en `Despacho` para entrega por motorizado (W-05).
- [ ] El motorizado valida el producto dañado y comprobante físico. Al canjearlo con éxito, el artículo dañado se asienta como `merma_averiada`.
- [ ] Se permiten hasta 3 intentos adicionales de cambio en campo; si se agotan, pasa a `escalado_cerrado` y el nuevo producto regresa a stock disponible (RF-04.3, ADR 0003).

### Contingencia de stock manual
- [ ] El backoffice permite alta y edición total de producto (todos los campos del PRD) y actualización directa de existencias.

## Puntos Abiertos resueltos (PRD v1.6 / v1.7 / v1.8)

- **PA-01 (reserva de stock):** **RESUELTO (v1.6).** TTL de reserva de **24 horas** con liberación automática por timeout/expiracion (ADR 0011).
- **PA-02 ("Precios bajos"):** **RESUELTO (v1.6).** Asignación **manual** de la etiqueta por el operador/farmacéutico en la ficha del producto (sin regla calculada).
- **PA-03 (OCR stock mixto):** **RESUELTO (v1.6).** Se **descarta la inserción parcial**; si falta cualquier medicamento, se suspende toda la receta y se alertan los faltantes (ADR 0008).
- **PA-04 (reclamos):** **RESUELTO (v1.6).** Reclamos como **sub-flujo posterior manual** tras `Entregado`, sin estados adicionales (ADR 0003).
- **PA-05 (reportería):** **RESUELTO (v1.6).** La Matriz de Reportería del Backoffice se incorpora al alcance mediante **RF-08** (ADR 0020).
- **PA-06 (reserva por tipo de sesión):** **RESUELTO (v1.7).** El cliente **guest** reserva solo al llegar al checkout; el **autenticado** reserva al agregar al carrito; ambos con TTL de 24h y liberación automática (RF-03.5, ADR 0016).
- **PA-07 (parámetros anti-abuso de reserva):** **RESUELTO (v1.8).** Límites de cara al cliente (3 unidades/SKU, 10 productos guest) y controles técnicos (1 req/s con burst 5 al agregar, 3 inicios de checkout por minuto por IP, techo de 1 checkout guest activo con reservas o máx. 15 unidades por IP) (RF-03.6, ADR 0016).

## Riesgos técnicos restantes

- **Disponibilidad 99.5% en un solo nodo** (ADR 0014): el KPI queda expuesto a punto único de fallo físico; respaldos y recuperación delegados a fase de operaciones.
