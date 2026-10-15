# ADR 0013: Consistencia pago + liberación de stock (transacciones nativas)

## Estado

Aceptado

## Contexto

`AGENTS.md` §5 permite "Patrón Saga o transacciones MySQL nativas" para flujos que involucren la
pasarela de pagos y la liberación de stock. En un monolito con una única base MySQL (ADR 0001,
0009), el pago (Stripe test, RF-06) y la confirmación/liberación de stock ocurren en el mismo
datastore.

## Decisión

Garantizar la consistencia del flujo pago → confirmación/liberación de stock con **transacciones
MySQL nativas** y **claves de idempotencia** por intento de pago (para reintentos de Stripe webhook
sin doble cargo ni doble decremento).

## Alternativas consideradas

- **Saga con pasos compensables por el broker** — necesario solo si pago y stock vivieran en
  servicios/DB separados; en un monolito es sobredimensionado.

## Consecuencias

- Atomicidad y corrección simple y verificable con una sola DB.
- Trade-off: la transacción acopla pago y stock en el mismo commit; si Stripe responde tarde, la
  transacción retiene la fila de stock más tiempo, lo que exige timeouts e idempotencia cuidadosos.
