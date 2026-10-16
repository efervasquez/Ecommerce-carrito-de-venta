# ADR 0013: Consistencia pago + liberación de stock (checkout en dos fases)

## Estado

Aceptado (v2 — reescrito tras revisión adversarial C-02)

## Contexto

`AGENTS.md` §5 permite "Patrón Saga o transacciones MySQL nativas" para flujos que involucren la
pasarela de pagos y la liberación de stock. En un monolito con una única base MySQL (ADR 0001,
0009), el pago (Stripe test, RF-06) y la confirmación/liberación de stock ocurren en el mismo
datastore.

La versión anterior de este ADR (v1) decidía transacciones MySQL nativas con claves de
idempotencia, pero **no definía el flujo secuencial**: cuándo se abre la transacción, cuándo se
cierra y qué pasa si el webhook de Stripe nunca llega. La revisión adversarial (C-02) identificó
que sin esta definición, el implementador podría abrir una transacción antes de llamar a Stripe
y mantener row-level locks en la tabla `Stock` durante 10–30 segundos (latencia de Stripe),
bloqueando a los 249 usuarios restantes y causando timeouts en cascada bajo carga.

## Decisión

Garantizar la consistencia del flujo pago → stock con un **checkout en dos fases** que evita
transacciones largas:

### Fase 1: Inicio de checkout (sin TX larga + prórroga de reserva C-02)

1. El cliente solicita `POST /api/v1/checkout`.
2. El backend **valida** que las reservas del carrito siguen vigentes (consulta sin lock:
   `SELECT ... WHERE reserva_expira_en > NOW()`).
3. Si las reservas son válidas:
   - Se cambia el estado del carrito a **`en_pago`**.
   - Se otorga una **prórroga temporal exclusiva de 10 minutos adicionales** a la reserva (`reserva_expira_en = NOW() + INTERVAL 10 MINUTE`),
     bloqueando la acción del job de purga de carritos (ADR 0011) mientras el cliente digita su tarjeta y autentica 3D Secure.
4. Se crea un `PaymentIntent` en Stripe con una **clave de idempotencia** (`idempotency_key = f"pedido-{carrito_id}-{intento}"`).
5. Se devuelve el `client_secret` del PaymentIntent al frontend para completar el pago en el navegador (Stripe.js).
6. **No se abre ninguna transacción MySQL larga.** Las reservas de stock prorrogadas protegen contra sobreventa.

### Fase 2: Webhook de confirmación (TX MySQL corta)

1. Stripe envía el webhook `payment_intent.succeeded` al backend.
2. El backend verifica la firma del webhook (Stripe signing secret).
3. Se busca la clave de idempotencia en la tabla `Pago`. **Si ya existe un pago confirmado con
   esa clave, se responde HTTP 200 sin procesar** (idempotencia ante webhooks duplicados).
4. Se abre una **transacción MySQL corta** (< 100ms):
   - Se invoca `InventoryProviderProtocol.confirm_deduction_batch` (ADR 0012) dentro de la transacción activa:
     - Si el stock reservado está conforme, se convierte en **decremento definitivo**.
     - **Salvaguarda ante quiebre físico imprevisto (Opción B / C-02):** Si ocurriese una inconsistencia
       física en almacén y no existiera stock, el pedido se crea en estado especial **`incidencia_stock`**.
       Esto dispara una alerta prioritaria al farmacéutico supervisor para abastecimiento de urgencia entre
       sucursales o contacto directo con el cliente, resolviendo la entrega física sin infringir la política
       de no reembolso del PRD RF-04.2.
   - Se crea el registro `Pedido` con estado `Registrado` (o `incidencia_stock`). Si contiene fármacos
     bajo receta médica, se marca con `auditoria_receta_pendiente = true` (W-03).
   - Se crea el registro `Pago` con la referencia de Stripe y la clave de idempotencia.
   - Se marca el carrito como `completado`.
5. Se hace `COMMIT`.
6. Se publica un evento `pedido.confirmado` en la cola `email.critico` y `despacho.organizar` en RabbitMQ.

### Caso de fallo: webhook nunca llega

- Si Stripe no envía el webhook, la prórroga de 10 minutos expira y el job de purga (ADR 0011)
  libera las reservas automáticamente.
- Stripe reintenta webhooks durante 72 horas con backoff. Si tras agotar reintentos el webhook
  no se procesa, el pago queda en Stripe sin pedido asociado; esto se detecta con un **job de
  reconciliación** programado (Tarea de Windows) que compara pagos en Stripe vs. pedidos en MySQL
  y alerta discrepancias en el log estructurado.

### Caso de fallo: pago rechazado o cancelado

- Stripe envía `payment_intent.payment_failed`. El backend recibe el webhook, registra el fallo,
  revierte el estado del carrito de `en_pago` a `activo`, y si el cliente abandona, las reservas se
  liberan inmediatamente para no retener stock innecesariamente.

## Alternativas consideradas

- **TX larga que abre antes de Stripe y cierra después del webhook** — atomicidad simple, pero
  mantiene row-level locks durante toda la latencia de Stripe (10–30s o más), causando contención
  severa en la tabla `Stock` bajo 250 usuarios concurrentes. Descartado.
- **Saga con pasos compensables por el broker** — necesario solo si pago y stock vivieran en
  servicios/DB separados; en un monolito es sobredimensionado.

## Consecuencias

- La TX MySQL dura < 100ms (solo operaciones locales), eliminando el riesgo de locks prolongados.
- La reserva previa (ADR 0011) actúa como protección contra sobreventa durante la ventana entre
  el inicio del checkout y la llegada del webhook.
- Trade-off: existe una ventana temporal entre "usuario ve confirmación en Stripe" y "webhook
  llega al backend" donde el pedido aún no existe en MySQL. Si el usuario consulta sus pedidos
  inmediatamente, no lo verá. Mitigación: mostrar en el frontend un estado "Procesando pago..."
  hasta que el polling o WebSocket confirme la creación del pedido.
- Se necesita un job de reconciliación Stripe ↔ MySQL para detectar discrepancias (webhooks
  perdidos, pagos sin pedido).
