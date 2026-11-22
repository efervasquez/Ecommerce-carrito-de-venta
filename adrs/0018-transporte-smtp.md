# ADR 0018: Transporte de correo transaccional (relay externo)

## Estado

Aceptado

## Ámbito

Historia de usuario — HU-01 (Autoregistro), HU-02 (Recuperación) y HU-08 (confirmación de pedido).

## Contexto

El sistema depende del envío de correos para los flujos más básicos del MVP: activación de cuenta
(ADR 0017), recuperación de contraseña (ADR 0017) y confirmación de pedido. El PRD §7 asume que
"el canal de mensajería SMTP posee la capacidad para despachar inmediatamente correos". Sin
embargo, la revisión adversarial (C-04) identificó que no existía ningún ADR ni diseño que
definiera el proveedor SMTP, la entregabilidad, los reintentos ni las implicaciones LPDP del
transporte de correo.

Un servidor SMTP on-premise (ej. hMailServer) sin reputación de IP y sin configuración
SPF/DKIM/DMARC correcta tiene alta probabilidad de que los correos lleguen a la carpeta de spam
de Gmail, Outlook y otros proveedores. Si el correo de activación llega a spam, el usuario no
puede registrarse y el MVP falla en su flujo más fundamental.

## Decisión

Usar un **relay externo de correo transaccional** con API REST oficial (preferencia inicial
**Brevo** [ex-Sendinblue] en su tier gratuito de 300 emails/día, o **SendGrid** como alternativa
homologada) para el despacho de correos del sistema:

### Proveedor y dimensionamiento de cuota (C-04)

- **Brevo Free Tier**: **300 emails/día** (el triple que el tier de 100 de SendGrid). Provee un
  margen seguro para el volumen inicial de la botica sin costos de tarjeta.
- **Alternativa / Contingencia:** SendGrid (100 emails/día) o Mailgun.
- **Regla de escalado a producción:** Si el volumen de ventas y registros supera los **200 correos/día
  sostenidos**, se transiciona automáticamente al tier transaccional de pago (~$15 USD/mes para
  40,000 envíos), considerado gasto operativo básico del e-commerce.

### Integración técnica y segmentación de colas (C-04)

- Los correos se publican en RabbitMQ segmentados por criticidad:
  - `email.critico`: Confirmación de pago y pedidos (prioridad máxima; nunca se ve afectada por
    ataques sobre el login o registro).
  - `email.auth`: Enlaces de activación y recuperación de contraseña (sujetos al cooldown de 15 min de ADR 0017).
- El worker en segundo plano (Servicio de Windows, ADR 0007) consume estas colas y ejecuta la
  llamada HTTP a la API REST del proveedor.
- Reintentos: 3 reintentos con backoff exponencial (1s, 4s, 16s), y derivación a `dlq.email` con log
  estructurado `ERROR` y `correlation_id` para trazabilidad.

### Entregabilidad

- Configurar **SPF, DKIM y DMARC** en los registros DNS del dominio de Botica la Luz, según las
  guías del proveedor elegido.
- Usar un **dominio de envío dedicado** (ej. `correo.boticaluz.pe`) para aislar la reputación
  transaccional del dominio principal.

### Dato que sale de la red

- El contenido del correo (dirección de email del destinatario + link con token) **no es dato de
  salud**. Las recetas médicas nunca se envían por email. El historial de compra no se incluye en
  los correos transaccionales del MVP.
- Esta salida de red está justificada por la criticidad del flujo (sin email no hay registro) y
  es aceptable bajo LPDP porque solo transita la dirección de email (dato personal básico, no
  dato sensible de salud).

### Tipos de correo en el MVP

| Tipo | Trigger | Contenido |
|------|---------|-----------|
| Activación de cuenta | Registro exitoso | Link con token de activación (ADR 0017) |
| Recuperación de contraseña | Solicitud de recuperación | Link con token de recuperación (ADR 0017) |
| Confirmación de pedido | Webhook de Stripe confirma pago | Resumen del pedido, número de orden, estado |

## Alternativas consideradas

- **SMTP on-premise (hMailServer en Windows)** — dato 100% local, cero costo. Descartado porque
  un SMTP sin reputación de IP tiene probabilidad alta de caer en spam. Configurar reputación,
  IP warming y compliance anti-spam es una operación compleja que excede el alcance del equipo
  para el MVP.
- **Híbrido: relay externo para transaccionales + SMTP local como fallback** — añade complejidad
  operativa (dos caminos de envío, dos puntos de falla) sin beneficio claro para el MVP.

## Consecuencias

- Alta entregabilidad desde el día 1 sin operación de servidor de correo.
- Trade-off: dependencia de un servicio externo (SendGrid); si SendGrid cae, los correos se
  encolan en RabbitMQ y se reintentan. Si la caída es prolongada, los usuarios no pueden
  activar cuentas hasta que el servicio se recupere.
- Costo potencial post-MVP si el volumen supera el free tier (previsible y bajo).
- Se necesita acceso a la configuración DNS del dominio de Botica la Luz para SPF/DKIM/DMARC.
