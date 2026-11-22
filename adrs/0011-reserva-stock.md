# ADR 0011: Reserva de stock (reserva al agregar + TTL 24h + purga)

## Estado

Aceptado

## Ámbito

Historia de usuario — HU-05 (Carrito de compras) y HU-07 (Pasarela de pagos).

## Contexto

El PRD RF-03.4 y §3 describen "selección y reserva de productos ligada estrictamente a la duración
de la sesión". Para evitar sobreventa, el stock debe reservarse al agregar al carrito. PA-01 quedó
RESUELTO (31/10/2026): la reserva tiene una vigencia de 24 horas y se libera automáticamente por
timeout/expiracion sin concretar la compra, devolviendo las unidades al stock disponible. `AGENTS.md`
§9 exige purgar carritos abandonados mediante Tareas programadas de Windows.

## Decisión

Reservar stock **al agregar al carrito** (aplica al cliente **autenticado**), con un campo de reserva y
**TTL de expiración de 24 horas** (PA-01). El cliente **guest** reserva stock solo al llegar al checkout;
el punto de reserva por tipo de carrito se define en **ADR 0016** (PA-06, RF-03.5). Un **job programado (Tarea de Windows)**
libera las reservas y purga los carritos cuyo TTL venció. El valor del TTL se configura, no se harcodea,
para permitir ajustes sin redespliegue.

### Prórroga Temporal de Reserva en Checkout (C-02)

Para prevenir la condición de carrera donde la reserva expira mientras el usuario digita su tarjeta
o completa la autenticación bancaria (3D Secure):
- Al invocar `POST /api/v1/checkout`, si la reserva está vigente, el carrito cambia al estado
  `en_pago` y se le otorga una **prórroga temporal exclusiva de 10 minutos adicionales**.
- Mientras el carrito permanezca en `en_pago`, el job programado de purga **no puede liberar el stock**
  a menos que venza la prórroga de 10 minutos sin resolución.
- Si el webhook de Stripe confirma éxito, la reserva se convierte en venta definitiva; si notifica
  rechazo (`payment_failed`), el stock se libera inmediatamente.

## Alternativas consideradas

- **Reservar solo en checkout** — menos retención de stock, pero riesgo severo de sobreventa y UX
  frustrante si el producto se agota mientras el cliente navegaba el catálogo.
- **Reservar sin prórroga en checkout** — descartado por C-02: permite que la purga libere el stock
  mientras el usuario está pagando en Stripe, provocando cobros sin existencias y violando la
  política de no reembolso.

## Consecuencias

- Sin sobreventa y consistencia garantizada por reserva + liberación automática + prórroga segura en
  checkout.
- Trade-off: stock "retenido" por carritos que nunca se convierten en venta; el TTL de 24h debe
  balancear disponibilidad vs. riesgo de abandono, y los límites anti-abuso de ADR 0016 amortiguan la
  retención anónima prolongada.
