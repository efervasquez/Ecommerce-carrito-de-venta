# ADR 0003: Modelo de datos (entidades, categorías y carrito guest)

## Estado

Aceptado

## Ámbito

Transversal — modelo de datos compartido por todas las historias de usuario.

## Contexto

El PRD describe, de forma explícita o implícita, las entidades que el sistema debe persistir para
soportar autoregistro, catálogo con atributos comerciales, carrito con reserva, pedidos con ciclo
de vida, pagos, reclamos, OCR y gestión manual de stock. El `AGENTS.md` §1 menciona además
"catálogo agrupado por categorías", que el PRD no pide explícitamente. El PRD define el carrito
"ligado estrictamente a la duración de la sesión del cliente".

## Decisión

Persistir en MySQL las entidades y relaciones:

- **Usuario** (roles RBAC: cliente, motorizado, admin/farmacéutico/operador): email, password_hash, rol, estado (`pendiente_activacion`, `activo`, `suspendido`).
- **Token** (ADR 0017): token_hash, tipo (`activacion`, `recuperacion`), usuario_id, expira_en, usado_en, creado_en.
- **Categoría** y relación `Producto -> Categoría` (se incluye categoría aunque el PRD no la liste: la exige `AGENTS.md`).
- **Producto**: nombre, fotos, componentes (principios activos), precio_regular, presentación, detalle, flag `requiere_receta`, `oferta_pct`, flag `precios_bajos`, contraindicaciones, precauciones, reacciones_adversas, métodos de entrega (`delivery`, `retiro`).
- **Stock** por producto: disponible y reservado (ver ADR 0011).
- **Sesión** (guest o autenticada) y **Carrito + CarritoItem** ligados a la sesión (con límites anti-abuso según ADR 0016).
- **Zona**: catálogo geográfico de cobertura (`id`, `nombre`, `distrito`, `tiempo_estimado_min`, `activo`) para agrupación logística.
- **Dirección**: `id`, `usuario_id`, `zona_id` (FK), `direccion_linea1`, `referencia`, `telefono_contacto`.
- **Pedido**: ítems, cliente (`usuario_id`), `direccion_id`, `zona_id` (para ruteo eficiente), método de entrega, tipo (`venta`, `reposicion`), `reclamo_id` (FK nullable hacia Reclamo si es reposición), `receta_id` (FK nullable), flag `auditoria_receta_pendiente` (bloquea pase a preparación hasta visto bueno farmacéutico si contiene medicamentos bajo receta, W-03), estado (`Registrado`, `Preparando producto`, `En camino`, `Entregado`, `incidencia_stock`), `despacho_id` (FK nullable hacia `Despacho`) y su **Pago** (Stripe test, clave de idempotencia; ver ADR 0013 v2).
- **Despacho (Ruta de Despacho)**: agrupación logística consolidada por cercanía (`id`, `zona_id`, `motorizado_id` [FK Usuario], `estado` [`asignado`, `en_ruta`, `cerrado`], `fecha_salida`, `fecha_cierre`). Relación 1:N con `Pedido` (un despacho agrupa N pedidos confirmados de venta o reposición pertenecientes a la misma zona para un motorizado por orden de llegada o auto-asignación, cumpliendo RF-07.1 y RF-07.2).
- **Receta/OCRJob** con documento, resultado de extracción y estado (éxito/quiebre de stock; ver ADR 0008). Vinculable al carrito/pedido para autorizar la compra de fármacos con `requiere_receta = true`.
- **Reclamo**: pedido_origen_id, fotos del producto dañado, comprobante de pago, número de reintentos en campo (máx. 3 intentos adicionales; RF-04.3), estado (`pendiente`, `aprobado`, `en_ruta_reposicion`, `cerrado_exitoso`, `escalado_cerrado`). Al aprobarse, genera un `Pedido` derivado con `tipo = 'reposicion'` y total 0.00, reservando y descontando el stock del nuevo ítem y asignándose a `Despacho` (W-05). En campo, la devolución exitosa asienta el medicamento dañado como `merma_averiada`; si se agotan los 3 intentos, el nuevo producto regresa a stock disponible.

El carrito se soporta **en sesión guest y se vincula al usuario al autenticarse** (puede armarse
antes del registro), protegido por los límites de cantidad y rate limiting de ADR 0016.

## Alternativas consideradas

- **Sin categorías** — alinear solo con el PRD; descartado porque `AGENTS.md` las exige y agrupar
  el catálogo aporta navegabilidad sin costo alto.
- **Carrito solo autenticado** — más simple y seguro, pero obliga a registrarse antes de agregar
  productos, introduciendo fricción en el embudo de compra.

## Consecuencias

- El modelo cubre todos los flujos del PRD y el requisito de catálogo agrupado.
- Trade-off: soportar carrito guest exige reconciliar la sesión guest con el usuario al autenticarse
  (merge de carrito) y aumenta la superficie a proteger contra abuso de reservas anónimas.
