# ADR 0007: Bus de eventos y workers (RabbitMQ + async workers)

## Estado

Aceptado

## Ámbito

Transversal — bus de eventos compartido por despacho (HU-08), OCR (HU-06), correo (HU-01/02/08) y catálogo (HU-03).

## Contexto

`AGENTS.md` obliga a desacoplar los flujos asíncronos por un "broker de mensajería local" (RabbitMQ
o Mosquitto) y menciona hilos asíncronos o Celery sobre Windows para tareas en segundo plano. Los
flujos a desacoplar son: pedido confirmado → despacho, OCR → resultado, envío de correos
(link de activación de un solo uso, recuperación) y purga de carritos abandonados. El usuario evaluó Kafka y
lo descartó por no correr nativo en Windows y por su consumo de RAM (en contra de `AGENTS.md` §9).

## Decisión

Usar **RabbitMQ** como bus de eventos local y **workers asíncronos en un proceso dedicado (Servicio de Windows)**
compartiendo el mismo código base (`python -m src.workers.main`), supervisado mediante **NSSM** (C-03).
No se ejecutan dentro del proceso web de FastAPI/IIS para evitar suspensión por *Idle Timeout* o duplicación por *Web Gardens*.

### Segmentación de Colas y Prioridad de Mensajería (C-04)

Para evitar que ráfagas o intentos de spam sobre el autoregistro saturen las notificaciones transaccionales de compras pagadas:
- `email.critico`: Confirmaciones de pedidos pagados y alertas de despacho (alta prioridad).
- `email.auth`: Enlaces de activación de cuenta y recuperación de contraseña (con cooldown y prioridad estándar).
- `ocr.procesar`: Recepción de imágenes y PDFs de recetas médicas.
- `catalogo.sincronizar`: Eventos de mutación de catálogo para Meilisearch.

### Control de Concurrencia y Calidad de Servicio (QoS / S-04)

Cada consumidor async (`aio-pika`) fija un `prefetch_count` explícito para no absorber masivamente mensajes en la memoria RAM del servidor:
- Cola `ocr.procesar`: `prefetch_count = 2` (alineado a los 2 hilos máximos de Tesseract en ADR 0008).
- Colas `email.*`: `prefetch_count = 10`.
- Cola `catalogo.sincronizar`: `prefetch_count = 20`.

## Alternativas consideradas

- **Kafka** — evaluado y descartado por el usuario: requiere Linux/WSL2 y es pesado en RAM para el
  hardware limitado.
- **Mosquitto (MQTT)** — ligero y free, pero MQTT es pub/sub orientado a IoT; incómodo para colas de
  tareas con confirmación y reintentos.
- **Celery + Redis** — estándar Python, pero el soporte de Celery en Windows es frágil y suma dos
  servicios.
- **Workers integrados en el ciclo de vida de FastAPI** — descartado por C-03: se apagan con el Idle
  Timeout de 20 min de IIS y colisionan si IIS escala a múltiples procesos.

## Política de reintentos y dead-letter (ampliado tras revisión adversarial W-09)

Cada cola de trabajo tiene asociada una **dead-letter exchange (DLX)** con su cola de dead-letter
correspondiente. La política de reintentos es uniforme para todas las colas:

1. **3 reintentos** con **backoff exponencial**: 1 s → 4 s → 16 s.
   - El backoff se implementa con `x-message-ttl` en colas de reintento intermedias (delayed
     retry pattern nativo de RabbitMQ, sin plugins).
2. Tras agotar los 3 reintentos, el mensaje se envía a la **dead-letter queue (DLQ)** del tipo
   correspondiente (ej. `dlq.email`, `dlq.ocr`, `dlq.despacho`).
3. Los mensajes en DLQ **no se descartan**: quedan disponibles para inspección manual y
   reprocesamiento.
4. La llegada de un mensaje a DLQ genera una **alerta en el log estructurado** (nivel `ERROR`)
   con el `correlation_id` del evento original para trazabilidad.

### Idempotencia

Cada consumidor debe ser **idempotente**: procesar el mismo mensaje dos veces produce el mismo
resultado sin efectos secundarios (ej. no enviar el correo dos veces, no decrementar stock dos
veces). La idempotencia se garantiza con claves únicas por evento almacenadas en MySQL.

### Observabilidad

- Habilitar el **RabbitMQ Management Plugin** (interfaz web en puerto 15672, accesible solo desde
  la red interna) para monitorear colas, mensajes encolados, tasas de consumo y DLQs.
- Configurar **alertas por tamaño de cola**: si una cola supera N mensajes pendientes (umbral
  configurable), se registra un `WARNING` en el log estructurado.

## Consecuencias

- Desacoplamiento real de despacho/OCR/notificaciones con colas duraderas, ACKs y reintentos
  controlados.
- Los mensajes que fallan permanentemente no se pierden ni se reintentan infinitamente: van a DLQ
  con alerta.
- Trade-off: un servicio más (RabbitMQ) a operar en Windows, y la necesidad de garantizar
  idempotencia en los consumidores para reintentos seguros. El delayed retry pattern con colas
  intermedias añade complejidad de topología en RabbitMQ.
