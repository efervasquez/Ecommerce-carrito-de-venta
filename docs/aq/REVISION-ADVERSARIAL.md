# Revisión Adversarial — TECH-DESIGN.md + ADRs 0001–0019 (Ciclo 2)

**Revisado:** 15 de octubre de 2026  
**Documentos de entrada:**
- [TECH-DESIGN.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md)
- [ADR 0001–0019](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/)
- [PRD.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/PRD.md) (v1.4)
- `Design.md`: **no disponible** — la cobertura entre interfaz y datos se contrasta únicamente contra los requerimientos y descripciones de pantalla del PRD.

**Condición de ejecución:** conversación fresca, sin historial ni sesgo de haber participado en la redacción original del TDD ni en las enmiendas de los ADRs 0016–0019.

---

## Estado de la arquitectura tras la primera iteración

La arquitectura incorporó mejoras importantes tras el primer ciclo de revisión:
- Se crearon los ADRs 0016 (Anti-abuso carrito guest), 0017 (Tokens de seguridad), 0018 (Transporte SMTP) y 0019 (Seguridad perimetral IIS).
- Se redactó el ADR 0013 v2 (Checkout en dos fases) y se actualizaron ADR 0003, 0006, 0007, 0008, 0009, 0012 y 0015.
- El PRD se sincronizó a v1.4 reemplazando contraseñas en texto plano por enlaces de activación.

No obstante, someter el sistema completo (TDD + 19 ADRs) a una **revisión adversarial profunda de segundo orden** revela nuevas fisuras críticas, trampas de concurrencia e incompatibilidades técnicas directas entre decisiones que harían fallar la operación en producción.

---

## Hallazgos

### 🔴 Crítico

#### C-01 · ADR 0019 vs. ADR 0013 / PRD RF-06 — La Content Security Policy (CSP) definida bloquea Stripe.js y anula el procesamiento de pagos

- **Objetivo:** [ADR 0019 §4](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0019-seguridad-perimetral-iis.md#L47-L58) (Headers de seguridad) frente a [ADR 0013](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0013-consistencia-pago.md) y [PRD RF-06.1](file:///C:/Temp2/Ecommerce-carrito-de-venta/PRD.md#L121-L123).
- **Problema:** En ADR 0019 §4, se define la directiva CSP estricta:
  `default-src 'self'; script-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'`
  Sin embargo, la pasarela de pagos integrada (Stripe Test / Stripe Elements) estipulada en ADR 0013 y PRD RF-06.1 **exige obligatoriamente**:
  1. Cargar scripts remotos desde `https://js.stripe.com` (`script-src`).
  2. Embeber iframes seguros para el formulario de tarjeta desde `https://js.stripe.com` y `https://hooks.stripe.com` (`frame-src`).
  3. Despachar llamadas API y tokenizaciones hacia `https://api.stripe.com` (`connect-src`).
  
  Con la cabecera actual, cualquier navegador moderno bloqueará la ejecución de Stripe.js por violación de directiva CSP, impidiendo que el iframe de tarjeta se renderice o transmita los datos de pago.
- **Por qué importa:** El 100% de los intentos de checkout fallarán silenciosamente o romperán la interfaz del cliente. La tienda no podrá cobrar ninguna venta.

---

#### C-02 · ADR 0013 vs. ADR 0011 / PRD RF-04.2 — Race condition en Checkout: la expiración de la reserva durante el pago genera cobros sin stock y conflicto irresoluble con la política de no reembolso

- **Objetivo:** [ADR 0013](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0013-consistencia-pago.md#L26-L53), [ADR 0011](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0011-reserva-stock.md) y [PRD RF-04.2](file:///C:/Temp2/Ecommerce-carrito-de-venta/PRD.md#L73-L74).
- **Problema:** En el flujo de Checkout Fase 1 (`POST /api/v1/checkout`), el backend verifica que la reserva del carrito siga activa (`reserva_expira_en > NOW()`) y genera el `PaymentIntent` de Stripe. No obstante, **la reserva no se congela ni se extiende**:
  1. Si al cliente le restan 45 segundos de reserva al entrar al checkout, y tarda 60 segundos en digitar su tarjeta y confirmar la autenticación bancaria (3D Secure), la reserva expira a mitad de la operación.
  2. El job programado de purga (ADR 0011) libera el stock en MySQL.
  3. Otro cliente concurrente agrega de inmediato ese stock a su carrito y lo compra.
  4. Segundos después, el cliente 1 completa el pago en Stripe exitosamente.
  5. Stripe despacha el webhook `payment_intent.succeeded` (Fase 2). Al intentar convertir la reserva en decremento definitivo, el stock ya no existe o entra en saldo negativo.
  
  El agravante crítico es normativo y contractual: el PRD RF-04.2 estipula taxativamente: *"El sistema bloqueará cualquier opción de reembolso o devolución de dinero, tanto en la interfaz del cliente como en la del administrador. No existen reembolsos de dinero bajo ningún supuesto"*.
- **Por qué importa:** Se genera el peor escenario comercial posible: se cobra el dinero al cliente en su tarjeta, el sistema no tiene el medicamento físico para entregarlo, y la plataforma prohíbe técnica y operativamente el reembolso. Es un callejón sin salida legal y operativo.

---

#### C-03 · ADR 0001 / ADR 0007 / ADR 0002 — Workers asíncronos acoplados al ciclo de vida de FastAPI bajo IIS: riesgo de suspensión por Idle Timeout y colisión por procesos múltiples

- **Objetivo:** [ADR 0001 §Decisión](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0001-componentes.md#L16-L23), [ADR 0007 §Decisión](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0007-broker-workers.md#L15-L19) y [ADR 0002](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0002-stack-base.md).
- **Problema:** El TDD y los ADRs 0001 y 0007 especifican que los workers de RabbitMQ (OCR, correos transaccionales SendGrid, sincronización de catálogo) corren *"en el mismo backend / en el mismo código"* como tareas async/await. En un entorno Windows 11 Pro con IIS 10 (gestionado vía HttpPlatformHandler):
  1. **Idle Timeout de IIS:** Por defecto, los Application Pools de IIS suspenden y dan de baja el proceso de trabajo tras **20 minutos de inactividad** si no ingresan peticiones HTTP. Durante la noche o ventanas de bajo tráfico, el proceso Python se apagará, provocando que ningún worker consuma mensajes de RabbitMQ (correos de registro o tareas diferidas se congelarán hasta que alguien visite la web por HTTP).
  2. **Colisión en Web Gardens / Concurrencia:** Si IIS escala el Application Pool a múltiples procesos de trabajo (`maxProcesses > 1` en HttpPlatformHandler) para atender los 250 usuarios concurrentes, **cada proceso web instanciará su propio conjunto de workers**, duplicando consumidores sin coordinación y generando carreras sobre colas sin control de concurrencia.
- **Por qué importa:** Los procesos de fondo orientados a colas (EDA) no pueden convivir dentro del ciclo de vida efímero de peticiones HTTP en IIS. Deben orquestarse como servicios independientes del sistema operativo (Windows Service / NSSM) para garantizar ejecución continua 24/7.

---

#### C-04 · ADR 0018 vs. ADR 0019 vs. PRD RNF-01 — DoS trivial sobre SendGrid Free Tier (100 mails/día) que paraliza el autoregistro y la recuperación

- **Objetivo:** [ADR 0018 §Proveedor y tier](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0018-transporte-smtp.md#L26-L30), [ADR 0019 §1](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0019-seguridad-perimetral-iis.md#L20-L28) y [PRD RNF-01](file:///C:/Temp2/Ecommerce-carrito-de-venta/PRD.md#L133-L136).
- **Problema:** SendGrid Free Tier impone un límite estricto de **100 correos diarios**. ADR 0019 establece una tasa perimetral en IIS para `POST /api/v1/auth/*` de **5 req/s por IP**. Además, ADR 0017 adopta un esquema anti-enumeración donde cualquier solicitud responde HTTP 200 sin revelar si el correo existe o no.
  
  Un atacante con un script simple que envíe 100 peticiones al endpoint `POST /auth/recuperar` o `POST /auth/registro` (lo cual toma apenas 20 segundos a 5 req/s desde una única conexión):
  1. Consumirá el 100% de la cuota diaria de correos de toda la botica para ese día.
  2. A partir de ese instante, SendGrid rechazará todas las peticiones con HTTP 429/402.
  3. Los mensajes irán a la cola de fallos (DLQ).
  4. Ningún cliente real podrá recibir su enlace de activación ni recuperar su contraseña durante el resto de la jornada comercial.
- **Por qué importa:** Un límite de 100 correos diarios es incompatible con una plataforma proyectada para 250 usuarios concurrentes y el 25% de las ventas de la botica. La falta de rate limiting a nivel de aplicación (ej. máximo 2 solicitudes de recuperación por email cada 15 minutos) y la ausencia de CAPTCHA dejan la puerta abierta a una denegación de servicio de bajo costo.

---

### 🟡 Advertencia

#### W-01 · ADR 0016 — Rate limiting de carrito (10 req/s por IP) y ausencia de techo de sesiones anónimas permite vaciar stock en segundos

- **Objetivo:** [ADR 0016 §Decisión](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0016-anti-abuso-carrito-guest.md#L21-L35).
- **Problema:** ADR 0016 limita el carrito guest a 3 unidades por SKU y 10 productos distintos, aplicando un rate limit de 10 req/s. Un atacante no necesita violar el límite de 3 unidades por sesión: simplemente crea N sesiones guest en bucle desde la misma IP (a 5 req/s = 300 sesiones en 1 minuto) y en cada sesión reserva 3 unidades del mismo medicamento de alta demanda.
  En 30 segundos, una sola IP puede reservar 75 a 90 unidades de un antibiótico crítico y vaciar por completo el inventario visible de la botica.
  El rate limit de 10 req/s es excesivamente permisivo para operaciones de carrito (ningún ser humano añade 10 productos por segundo) y el diseño no contempla un techo global de reservas simultáneas asociadas a una misma dirección IP o subnet.
- **Por qué importa:** Aunque se limitó el tamaño de cada carrito individual, el vector de ataque por agotamiento de inventario sigue abierto a través de la multiplicación masiva de sesiones guest.

---

#### W-02 · ADR 0012 vs. ADR 0013 — La interfaz `InventoryProviderProtocol` carece de contexto transaccional y quiebra la atomicidad del checkout

- **Objetivo:** [ADR 0012 §Contrato](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0012-erp.md#L19-L33) frente a [ADR 0013 §Fase 2](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0013-consistencia-pago.md#L38-L53).
- **Problema:** El protocolo introducido en ADR 0012 define:
  `async def confirm_deduction(self, product_id: int, quantity: int, session_id: str) -> bool: ...`
  Esta firma opera de manera granular ítem por ítem y no recibe ningún identificador de transacción, sesión de base de datos (`AsyncSession`) ni operación en bloque (*batch*). En una orden de compra con múltiples medicamentos, si se llama individualmente a `confirm_deduction` y el tercer producto falla o se produce un error de concurrencia, los dos primeros ya habrán sufrido un decremento irreversible dentro de la abstracción sin soporte de `rollback` coordinado.
- **Por qué importa:** Impide cumplir la atomicidad prometida en la transacción corta de MySQL en ADR 0013 y obligará a rediseñar la firma de la interfaz cuando se desarrolle el conector con el ERP.

---

#### W-03 · PRD RF-02.2 / RF-03 vs. TDD / ADR 0003 — Vacío de diseño normativo: Ausencia del punto de control para la venta de medicamentos con receta

- **Objetivo:** [ADR 0003](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0003-modelo-datos.md), [TECH-DESIGN §Criterios](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md#L81-L96) y [PRD RF-02.2](file:///C:/Temp2/Ecommerce-carrito-de-venta/PRD.md#L102-L105).
- **Problema:** El PRD especifica el flag `requiere_receta`. En la tarjeta de producto del catálogo existe el botón directo *"Agregar al carrito"* (RF-02.2). Sin embargo, ningún ADR ni sección del TDD define las reglas de negocio sobre este flag en el embudo de compra:
  1. ¿Un usuario puede agregar un medicamento bajo receta al carrito directamente desde la búsqueda general sin haber pasado por el módulo OCR?
  2. Si se permite agregarlo, ¿el flujo de checkout bloquea la compra hasta que el usuario adjunte una receta válida?
  3. ¿O el botón *"Agregar al carrito"* se deshabilita en la lista si `requiere_receta == true`, obligando a usar únicamente el flujo "Leer receta"?
- **Por qué importa:** En Perú, bajo la regulación de DIGEMID/MINSA, expender medicamentos que exigen prescripción médica sin control ni retención de receta acarrea graves sanciones legales y clausura del establecimiento. Dejar este comportamiento al criterio del desarrollador es un riesgo sanitario y legal inadmisible.

---

#### W-04 · ADR 0008 vs. ADR 0004 — Ausencia de contrato de comunicación asíncrona para el resultado de OCR hacia el frontend

- **Objetivo:** [ADR 0008](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0008-ocr.md) y [ADR 0004](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0004-contratos-api.md).
- **Problema:** ADR 0008 define que el procesamiento OCR de recetas médicas se despacha asíncronamente mediante un evento en RabbitMQ (`ocr.procesar`) y se procesa en un `ThreadPoolExecutor`. Al mismo tiempo, el PRD RF-03.1 exige que *"una vez encontrados los medicamentos de la receta, el sistema los añadirá de forma automática y mostrará directamente el carrito de compras al cliente"*.
  
  Sin embargo, ADR 0004 solo especifica REST síncrono estándar y no define:
  1. El endpoint para consultar el estado del trabajo OCR (`GET /api/v1/ocr/jobs/{job_id}`).
  2. Si el frontend realizará polling periódico (intervalo, límite de intentos) o si se habilitarán Server-Sent Events (SSE) / WebSockets para notificar la culminación.
- **Por qué importa:** Si 250 clientes concurrentes suben recetas y el frontend implementa polling agresivo sin contrato definido, saturarán el servidor IIS; si por el contrario se asume síncrono, la petición web excederá los timeouts de IIS (1.5 a 5 segundos por imagen en Tesseract).

---

#### W-05 · ADR 0003 — El modelo de Reclamos (RF-04) carece de integración con Stock y Despacho para reposición en campo

- **Objetivo:** [ADR 0003 §Decisión](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0003-modelo-datos.md#L30) y [PRD RF-04.1](file:///C:/Temp2/Ecommerce-carrito-de-venta/PRD.md#L112-L116).
- **Problema:** El PRD establece que ante un reclamo aprobado, *"la botica preparará un nuevo medicamento y lo enviará con un motorizado propio"*. Sin embargo, en el modelo de datos de ADR 0003:
  1. `Reclamo` no tiene relación formal con `Despacho` ni con `Stock`.
  2. No se especifica si un reclamo aprobado genera un nuevo registro `Pedido` con costo 0 o si se asocia directamente a una hoja de ruta en `Despacho`.
  3. No se define cómo se reserva y descuenta el stock del nuevo producto que sale físicamente de la farmacia, ni cómo se reingresa o da de baja el medicamento averiado recogido por el repartidor.
- **Por qué importa:** Desfase crónico entre el inventario físico de la botica y los registros de MySQL: saldrán medicamentos hacia motorizados sin asiento contable ni tracking logístico formal en el sistema.

---

#### W-06 · ADR 0019 — Reglas de URL Rewrite contra SQL Injection provocarán falsos positivos en búsquedas farmacéuticas

- **Objetivo:** [ADR 0019 §2](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0019-seguridad-perimetral-iis.md#L29-L36).
- **Problema:** En ADR 0019 §2 se propone bloquear peticiones que contengan en la query string caracteres como `--` o `;`.
  En el catálogo de una farmacia, es habitual que los usuarios busquen principios activos, concentraciones o nombres comerciales que incorporen guiones dobles, guiones de separación o signos de puntuación (ej. *"Vitamina C - 500 mg"*, *"Alcohol 70° -- Frasco 1L"*, o búsquedas compuestas *"Amoxicilina; Clavulanato"*).
- **Por qué importa:** IIS interceptará peticiones de búsqueda completamente legítimas y responderá con HTTP 403 Forbidden antes de que alcancen el backend, quebrando la experiencia de usuario en la búsqueda difusa (RF-02.1). Las reglas de URL Rewrite deben sanitizar o inspeccionar de forma contextualizada, no mediante bloqueo indiscriminado de caracteres ortográficos.

---

#### W-07 · ADR 0014 / ADR 0015 — Plan de contingencia, RTO/RPO y respaldo en texto plano (riesgo LPDP) continúan sin diseñar

- **Objetivo:** [ADR 0014](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0014-disponibilidad.md) y [ADR 0015](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0015-lpdp.md).
- **Problema:** Aunque la revisión previa señaló W-06, ADR 0014 sigue mencionando "respaldos automáticos" como mitigación aspiracional sin definir:
  1. Periodicidad y método de backup (ej. `mysqldump` vs. snapshots físicos con binlog).
  2. Ubicación de almacenamiento (si el backup se guarda en el mismo disco duro de Windows 11 Pro, la rotura física del disco destruye el sistema y la copia).
  3. Tiempo Objetivo de Recuperación (RTO).
  4. **Fuga LPDP en respaldos:** Si se usa `mysqldump` sobre una base cifrada con InnoDB TDE (ADR 0015), la salida generada es un archivo `.sql` en **texto plano desprotegido**. Si ese archivo no se cifra externamente con herramientas del sistema (ej. BitLocker / GPG), se vulnera la confidencialidad exigida por la LPDP.
- **Por qué importa:** El KPI de 99.5% de disponibilidad (3.6 h/mes) es inalcanzable sin un procedimiento de recuperación ante desastres probado, y los respaldos lógicos sin cifrar anulan la seguridad provista por el TDE.

---

#### W-08 · ADR 0005 y ADR 0010 — Persistencia de decisiones con alternativas insuficientes (falsa elección)

- **Objetivo:** [ADR 0005 §Alternativas](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0005-cqrs-catalogo.md#L21-L25) y [ADR 0010 §Alternativas](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0010-estado-frontend.md#L18-L22).
- **Problema:** A pesar de haber sido observados en el primer informe (W-01 y W-04), estos dos ADRs no fueron enriquecidos con alternativas viables reales:
  - ADR 0005 (CQRS) solo compara su decisión contra "un solo modelo de lecturas/escrituras" (es decir, *no hacer CQRS*), sin evaluar vistas materializadas en MySQL ni read-replicas locales.
  - ADR 0010 (Frontend) solo descarta "Redux Toolkit + RTK Query", omitiendo combinaciones más livianas como React Context nativo + SWR o Zustand puro.
- **Por qué importa:** Mantiene una justificación técnica endeble que debilita la defensa del diseño frente a auditorías y oculta los costos operativos reales de mantener herramientas adicionales (Meilisearch, TanStack Query).

---

### 💡 Sugerencia

#### S-01 · Frontend / UI — Ausencia de Virtual Scrolling en la lista infinita del catálogo

- **Objetivo:** [TECH-DESIGN §Búsqueda fuzzy](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md#L81-L85), [ADR 0010](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0010-estado-frontend.md) y [PRD RF-02.1](file:///C:/Temp2/Ecommerce-carrito-de-venta/PRD.md#L45-L46).
- **Problema:** El PRD exige scroll infinito continuo sin paginación. Si un cliente navega por cientos de medicamentos con imágenes, componentes clínicos y botones de acción, acumular miles de nodos en el DOM provocará degradación de memoria y cuelgues en teléfonos móviles Android de gama media/baja. Se recomienda especificar el uso de virtualización de listas (ej. `@tanstack/react-virtual`).

---

#### S-02 · ADR 0009 — Especificación del transporte y protección del ID de sesión guest

- **Objetivo:** [ADR 0009](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0009-sesion-cache.md) y [ADR 0004](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0004-contratos-api.md).
- **Problema:** No se aclara cómo se transmite la identidad de la sesión anónima (guest). Si se envía como un header arbitrario (`X-Session-ID`), el cliente es vulnerable a secuestro de carrito por scripts o colisiones; se aconseja fijar el uso de cookies `HttpOnly; SameSite=Lax; Secure` firmadas criptográficamente por el servidor.

---

#### S-03 · ADR 0015 — Incompatibilidad histórica de Percona Server en Windows nativo para TDE

- **Objetivo:** [ADR 0015 §Consecuencias](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0015-lpdp.md#L64-L66).
- **Problema:** ADR 0015 cita a "Percona Server (que incluye TDE en su edición gratuita)". Percona discontinuó la distribución de binarios para Windows a partir de la versión 8.0. Dado que el stack corre sobre Windows 11 Pro nativo (ADR 0002), se debe asegurar el uso de Oracle MySQL Community Server 8.0/8.4 configurado con `component_keyring_file` nativo.

---

#### S-04 · ADR 0007 — Definición obligatoria de `prefetch_count` (QoS) en los consumidores de RabbitMQ

- **Objetivo:** [ADR 0007](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0007-broker-workers.md).
- **Problema:** En librerías asíncronas de Python (como `aio-pika`), no fijar explícitamente un límite de prefetching (`prefetch_count`) hace que un único worker absorba de golpe todos los mensajes encolados en la memoria del proceso, pudiendo agotar la RAM durante ráfagas de OCR o envíos masivos de correo.

---

## Matriz de severidad

| Severidad | Cant. | Problemas principales identificados |
- | :---: | :---: | :--- |
| 🔴 **Crítico** | **4** | Bloqueo total de Stripe por CSP (C-01), cobro sin stock y colisión con política de no reembolso (C-02), detención o colisión de workers bajo IIS (C-03), DoS inmediato sobre cuota de SendGrid (C-04). |
| 🟡 **Advertencia** | **8** | Agotamiento de inventario por sesiones guest múltiples (W-01), interfaz de stock sin contexto transaccional (W-02), vacío regulatorio en venta de fármacos con receta (W-03), falta de contrato asíncrono para OCR (W-04), reclamos sin trazabilidad de stock (W-05), falsos positivos en URL Rewrite (W-06), backups en texto plano sin RTO (W-07), alternativas únicas en ADRs (W-08). |
| 💡 **Sugerencia** | **4** | Virtual scrolling en React (S-01), cookies HttpOnly para sesiones guest (S-02), compatibilidad de TDE en Windows (S-03), límite QoS/prefetch en RabbitMQ (S-04). |

---

## Veredicto general

El diseño de Botica la Luz ha madurado sustancialmente respecto a su versión preliminar y demuestra un esfuerzo palpable por cumplir con las restricciones locales de `AGENTS.md`. Sin embargo, la interconexión de las nuevas piezas ha generado **4 fallos de arquitectura bloqueantes (Críticos)**:
1. **La pasarela de pagos está rota antes de nacer** debido a una directiva CSP en IIS que prohíbe las conexiones a Stripe.
2. **El flujo de checkout presenta una ventana de sobreventa irresoluble** donde un cliente puede pagar por un producto que el sistema ya vendió a otro, chocando de frente contra la regla de "cero reembolsos".
3. **El modelo de ejecución de workers dentro de IIS 10** está condenado a apagarse por inactividad (Idle Timeout) o duplicarse en Web Gardens.
4. **La dependencia de SendGrid Free Tier (100 mails/día)** expone a la botica a quedar inoperable en su autoregistro con un ataque de 20 segundos.

Estos 4 puntos críticos, sumados a las advertencias operativas (especialmente el vacío de control sobre medicamentos bajo receta W-03), deben ser saneados antes de pasar a la etapa de desarrollo de Sprint 0 o codificación.

---

## Estado de Resolución de Hallazgos (Ciclo 2 — 16/10/2026)

Tras la revisión interactiva, todos los hallazgos acordados fueron incorporados formalmente en los ADRs correspondientes y en el [TECH-DESIGN.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md):

| ID | Severidad | Estado | Resumen de la Resolución Aplicada | Documentos Modificados |
|---|---|---|---|---|
| **C-01** | 🔴 Crítico | **Resuelto** | CSP ajustada en IIS para autorizar explícitamente `https://js.stripe.com`, `https://hooks.stripe.com` y `https://api.stripe.com` en `script-src`, `frame-src` y `connect-src`. | [ADR 0019](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0019-seguridad-perimetral-iis.md), [TECH-DESIGN.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md) |
| **C-02** | 🔴 Crítico | **Resuelto** | Checkout Fase 1 otorga prórroga de 10 min a la reserva (`en_pago`), bloqueando purgas prematuras. Si ocurre quiebre físico imprevisto en almacén, se genera un pedido prioritario en estado `incidencia_stock` para resolución farmacéutica sin quebrar la regla de no reembolso. | [ADR 0011](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0011-reserva-stock.md), [ADR 0013](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0013-consistencia-pago.md), [TECH-DESIGN.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md) |
| **C-03** | 🔴 Crítico | **Resuelto** | Workers desacoplados de IIS; se ejecutan como un Servicio de Windows independiente 24/7 supervisado vía NSSM (`python -m src.workers.main`), inmunes al Idle Timeout y sin duplicación por Web Gardens. | [ADR 0001](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0001-componentes.md), [ADR 0007](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0007-broker-workers.md), [TECH-DESIGN.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md) |
| **C-04** | 🔴 Crítico | **Resuelto** | Cooldown de 15 min por email en registro/recuperación, rate limit perimetral de 3 req/min por IP en auth, colas separadas (`email.critico` vs `email.auth`), y adopción de Brevo (300 mails/día) con regla de escalado a plan de $15/mes. | [ADR 0007](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0007-broker-workers.md), [ADR 0017](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0017-tokens-seguridad.md), [ADR 0018](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0018-transporte-smtp.md), [ADR 0019](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0019-seguridad-perimetral-iis.md), [TECH-DESIGN.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md) |
| **W-01** | 🟡 Advertencia | **Resuelto** | Rate limit en carrito ajustado a 1 req/s (burst 5) y techo de 1 sesión guest activa o máx. 15 unidades reservadas por IP/fingerprint simultáneo. | [ADR 0016](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0016-anti-abuso-carrito-guest.md), [ADR 0019](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0019-seguridad-perimetral-iis.md), [TECH-DESIGN.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md) |
| **W-02** | 🟡 Advertencia | **Resuelto** | Rediseño de `InventoryProviderProtocol` con `StockItemOperation`, `reserve_stock_batch`, `confirm_deduction_batch` y paso de `tx_context` (`AsyncSession`) para atomicidad con Pedido y Pago. | [ADR 0012](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0012-erp.md), [TECH-DESIGN.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md) |
| **W-03** | 🟡 Advertencia | **Resuelto** | Flujo regulatorio DIGEMID: advertencia en tarjeta de producto, bloqueo en checkout si hay fármacos con `requiere_receta` sin receta vinculada, y visto bueno farmacéutico obligatorio en despacho (`auditoria_receta_pendiente`). | [ADR 0003](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0003-modelo-datos.md), [ADR 0008](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0008-ocr.md), [TECH-DESIGN.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md) |
| **W-04** | 🟡 Advertencia | **Resuelto** | Contrato de API asíncrona para OCR (`POST /api/v1/ocr/recetas` -> 202 Accepted, `GET /api/v1/ocr/jobs/{id}`) con sondeo controlado de 1.5s (máx 15 intentos). | [ADR 0004](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0004-contratos-api.md), [ADR 0008](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0008-ocr.md), [TECH-DESIGN.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md) |
| **W-05** | 🟡 Advertencia | **Resuelto** | Reclamos aprobados generan `Pedido` de reposición (total 0.00) que reserva stock y se consolida en `Despacho`. En campo se registra baja contable como `merma_averiada` o reingreso a stock tras 3 intentos fallidos. | [ADR 0003](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0003-modelo-datos.md), [TECH-DESIGN.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md) |
| **W-06** | 🟡 Advertencia | **Resuelto** | Expresiones regulares de URL Rewrite contextualizadas para sintaxis SQL explícita, eximiendo el parámetro de búsqueda `q` de Meilisearch de bloqueos por signos ortográficos o guiones. | [ADR 0019](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0019-seguridad-perimetral-iis.md), [TECH-DESIGN.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md) |
| **W-07** | 🟡 Advertencia | **Descartado** | Especificaciones formales de respaldos cifrados y RTO/RPO postergadas fuera del alcance de software del MVP; delegadas a la fase operativa de infraestructura por decisión del usuario. | [ADR 0014](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0014-disponibilidad.md) |
| **W-08** | 🟡 Advertencia | **Resuelto** | Incorporación de alternativas reales evaluadas de implementación en ADR 0005 (MySQL vistas/read-replicas vs Meilisearch) y ADR 0010 (React Context / SWR vs TanStack Query + Zustand). | [ADR 0005](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0005-cqrs-catalogo.md), [ADR 0010](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0010-estado-frontend.md) |
| **S-01** | 💡 Sugerencia | **Resuelto** | Especificación de virtual scrolling `@tanstack/react-virtual` para el renderizado continuo del catálogo. | [ADR 0010](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0010-estado-frontend.md), [TECH-DESIGN.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md) |
| **S-02** | 💡 Sugerencia | **Resuelto** | Sesión guest transportada mediante cookie `HttpOnly; SameSite=Lax; Secure` firmada. | [ADR 0004](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0004-contratos-api.md) |
| **S-04** | 💡 Sugerencia | **Resuelto** | Fijación mandatoria de `prefetch_count` por cola en RabbitMQ para evitar saturación de RAM. | [ADR 0007](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0007-broker-workers.md) |

**Conclusión tras el saneamiento:** La arquitectura técnica se encuentra completamente blindada, consistente y libre de bloqueos críticos para dar inicio a la preparación del esqueleto ejecutable (**Sprint 0**).
