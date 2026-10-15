# ADR 0003: Modelo de datos (entidades, categorías y carrito guest)

## Estado

Aceptado

## Contexto

El PRD describe, de forma explícita o implícita, las entidades que el sistema debe persistir para
soportar autoregistro, catálogo con atributos comerciales, carrito con reserva, pedidos con ciclo
de vida, pagos, reclamos, OCR y gestión manual de stock. El `AGENTS.md` §1 menciona además
"catálogo agrupado por categorías", que el PRD no pide explícitamente. El PRD define el carrito
"ligado estrictamente a la duración de la sesión del cliente".

## Decisión

Persistir en MySQL las entidades y relaciones:

- **Usuario** (roles RBAC: cliente, motorizado, admin/farmacéutico/operador): email, password_hash
  provisional, rol, estado, datos de entrega.
- **Categoría** y relación `Producto -> Categoría` (se incluye categoría aunque el PRD no la liste:
  la exige `AGENTS.md`).
- **Producto**: nombre, fotos, componentes (principios activos), precio_regular, presentación,
  detalle, flag `requiere_receta`, `oferta_pct`, flag `precios_bajos`, contraindicaciones,
  precauciones, reacciones_adversas, métodos de entrega.
- **Stock** por producto (disponible y reservado; ver ADR 0011).
- **Sesión** (guest o autenticada) y **Carrito + CarritoItem** ligados a la sesión.
- **Pedido** con ítems, cliente, zona/dirección, método de entrega, estado (`Registrado`,
  `Preparando producto`, `En camino`, `Entregado`) y su **Pago** (Stripe test).
- **Receta/OCRJob** con documento, resultado de extracción y estado (éxito/quiebre de stock).
- **Reclamo**: pedido, fotos, comprobante, intentos (máx. 3) y estado.
- **Despacho**: consolidación de rutas por zona, motorizado asignado, orden de llegada.

El carrito se soporta **en sesión guest y se vincula al usuario al autenticarse** (puede armarse
antes del registro).

## Alternativas consideradas

- **Sin categorías** — alinear solo con el PRD; descartado porque `AGENTS.md` las exige y agrupar
  el catálogo aporta navegabilidad sin costo alto.
- **Carrito solo autenticado** — más simple y seguro, pero obliga a registrarse antes de agregar
  productos, introduciendo fricción en el embudo de compra.

## Consecuencias

- El modelo cubre todos los flujos del PRD y el requisito de catálogo agrupado.
- Trade-off: soportar carrito guest exige reconciliar la sesión guest con el usuario al autenticarse
  (merge de carrito) y aumenta la superficie a proteger contra abuso de reservas anónimas.
