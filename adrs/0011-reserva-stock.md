# ADR 0011: Reserva de stock (reserva al agregar + TTL + purga)

## Estado

Aceptado

## Contexto

El PRD RF-03.3 y §3 describen "selección y reserva de productos ligada estrictamente a la duración
de la sesión". Para evitar sobreventa, el stock debe reservarse al agregar al carrito. El PRD deja
abierto PA-01: la duración exacta de la reserva y la regla de liberación automática (inactividad,
abandono o timeout). `AGENTS.md` §9 exige purgar carritos abandonados mediante Tareas programadas de
Windows.

## Decisión

Reservar stock **al agregar al carrito**, con un campo de reserva y **TTL de expiración**. Un **job
programado (Tarea de Windows)** libera las reservas y purga los carritos cuyo TTL venció. La
**duración exacta del TTL queda como parámetro** a definir por PM/BA (PA-01) y se configura, no se
harcodea.

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

- Sin sobreventa y consistencia garantizada por reserva + liberación automática + prórroga segura en checkout.
- Trade-off: stock "retenido" por carritos que nunca se convierten en venta; el TTL debe
  balancear disponibilidad vs. riesgo de abandono. Pendiente resolver PA-01 antes de fijar el valor.
