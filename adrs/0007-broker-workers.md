# ADR 0007: Bus de eventos y workers (RabbitMQ + async workers)

## Estado

Aceptado

## Contexto

`AGENTS.md` obliga a desacoplar los flujos asíncronos por un "broker de mensajería local" (RabbitMQ
o Mosquitto) y menciona hilos asíncronos o Celery sobre Windows para tareas en segundo plano. Los
flujos a desacoplar son: pedido confirmado → despacho, OCR → resultado, envío de correos
(contraseña provisional, recuperación) y purga de carritos abandonados. El usuario evaluó Kafka y
lo descartó por no correr nativo en Windows y por su consumo de RAM (en contra de `AGENTS.md` §9).

## Decisión

Usar **RabbitMQ** como bus de eventos local y **workers asíncronos (consumidores async/await)** en
el mismo backend para procesar los eventos publicados. No se usa Celery.

## Alternativas consideradas

- **Kafka** — evaluado y descartado por el usuario: requiere Linux/WSL2 y es pesado en RAM para el
  hardware limitado.
- **Mosquitto (MQTT)** — ligero y free, pero MQTT es pub/sub orientado a IoT; incómodo para colas de
  tareas con confirmación y reintentos.
- **Celery + Redis** — estándar Python, pero el soporte de Celery en Windows es frágil y suma dos
  servicios.

## Consecuencias

- Desacoplamiento real de despacho/OCR/notificaciones con colas duraderas, ACKs y reintentos.
- Trade-off: un servicio más (RabbitMQ) a operar en Windows, y la necesidad de garantizar
  idempotencia en los consumidores para reintentos seguros.
