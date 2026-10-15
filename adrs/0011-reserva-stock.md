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

## Alternativas consideradas

- **Reservar solo en checkout** — menos complejidad, pero riesgo de sobreventa y UX pobre (el
  carrito puede quedar sin stock al pagar).

## Consecuencias

- Sin sobreventa y consistencia garantizada por reserva + liberación automática.
- Trade-off: stock "retenido" por carritos que nunca se convierten en venta; el TTL debe
  balancear disponibilidad vs. riesgo de abandono. Pendiente resolver PA-01 antes de fijar el valor.
