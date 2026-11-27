# CONTRATO — HU-07 Pasarela de pagos Stripe Sandbox

**Tipo:** Feature
**Versión:** v2
**Estado:** Aprobado (2026-11-25, usuario humano)
**Origen:** `HUs/HU-07-pasarela-de-pagos-stripe-sandbox.md`

---

## Paquete de contexto

| Fuente | Por qué entra |
|---|---|
| `HUs/HU-07-pasarela-de-pagos-stripe-sandbox.md` | Historia, criterios de aceptación y escenarios Gherkin. |
| `TECH-DESIGN.md` §Checkout y pago (L110-114) | Prórroga en checkout, CSP Stripe, webhook atómico, `incidencia_stock`. |
| `adrs/0013-consistencia-pago.md` | Checkout en dos fases, idempotencia, webhook `payment_intent.*`, casos de fallo. |
| `adrs/0011-reserva-stock.md` | Reserva 24h + prórroga 10 min en checkout. |
| `adrs/0012-erp.md` | `InventoryProviderProtocol.confirm_deduction_batch` con `tx_context` (MVP local MySQL). |
| `adrs/0016-anti-abuso-carrito-guest.md` | Reserva guest en checkout, 3 checkouts/min/IP, 1 checkout guest activo. |
| `adrs/0003-modelo-datos.md` | Entidades `Zona`, `Direccion`, `Pedido` (estado `Registrado`/`incidencia_stock`) y `Pago`. |
| `adrs/0004-contratos-api.md` | REST versionado `/api/v1`, Pydantic, sesión guest por cookie. |
| `adrs/0007-broker-workers.md` | Eventos `pedido.confirmado` (cola `email.critico`) y `despacho.organizar`. |
| `adrs/0019-seguridad-perimetral-iis.md` | CSP que autoriza `js.stripe.com`, `hooks.stripe.com`, `api.stripe.com`. |
| `contratos/CONTRATO-HU-05.md` | `POST /api/v1/checkout` ya reserva stock para guest; HU-07 lo extiende sin romperlo. |

## Interfaz observable

- API HTTP: `GET /api/v1/zonas`, `GET|POST /api/v1/direcciones`, `POST /api/v1/checkout`, webhook `POST /api/v1/pagos/webhook`, estado `GET /api/v1/pagos/{payment_intent_id}`, pedido `GET /api/v1/pedidos/{numero_pedido}`.
- Pantalla `/checkout`: selección/captura de entrega + Stripe Elements (tarjeta) + botón `Pagar ahora`.
- Pantalla de confirmación con número de pedido, resumen y monto pagado.

## Comportamiento

### Sesión requerida para pagar

- El **pago** exige sesión **autenticada** de cliente. Un **guest** puede iniciar el checkout para reservar stock, pero **no** paga hasta autenticarse.
- Tras autenticarse, el carrito guest se vincula al usuario (ADR-0003) y puede continuar al pago.
- Cualquier endpoint de pago/pedido sin sesión válida responde **HTTP 401**.

### Captura de entrega

**Entradas**

```http
GET  /api/v1/zonas
GET  /api/v1/direcciones
POST /api/v1/direcciones
```

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| Zonas activas | `GET /api/v1/zonas` (auth) | HTTP 200; `[{ id, nombre, distrito, tiempo_estimado_min }]` solo zonas activas. | ADR-0003 |
| Direcciones del usuario | `GET /api/v1/direcciones` (auth) | HTTP 200; `[{ id, direccion_linea1, referencia, telefono_contacto, zona_id }]` del usuario. | ADR-0003 |
| Crear dirección | `POST /api/v1/direcciones` `{ direccion_linea1, referencia?, telefono_contacto, zona_id }` | HTTP 201; `{ id, ... }`. Valida zona existente y activa. | ADR-0003 |
| Faltan campos obligatorios | Cuerpo incompleto | HTTP 422. | **decisión propuesta** |
| Zona inexistente/inactiva | `zona_id` inválido | HTTP 409; `"Zona no disponible"`. | **decisión propuesta** |

### Inicio de checkout

**Entrada**

```http
POST /api/v1/checkout
Body (autenticado): { direccion_id?: int, metodo_entrega: "delivery" | "retiro" }
```

**Guest (sin sesión autenticada)**

| Caso | Salida esperada | Origen |
|---|---|---|
| Guest con carrito y sin reserva activa | HTTP 200; `{ requiere_autenticacion: true, reserva_expira_en }` (sin PaymentIntent). Crea reserva 24h; no cobra. | HU-07 crit.6 y esc.3; ADR-0016 |
| Guest con checkout/reserva activa por IP | HTTP 409; exige continuar como autenticado o liberar la reserva anterior. | ADR-0016; HU-05 |
| Más de 3 inicios/min/IP | HTTP 429. | ADR-0016 |

**Autenticado**

| Caso | Salida esperada | Origen |
|---|---|---|
| Camino feliz | HTTP 200; `{ payment_intent_id, client_secret, monto, moneda:"PEN", reserva_expira_en }`. Valida reserva o la crea, prorroga 10 min, carrito → `en_pago`, crea PaymentIntent con clave `pedido-{carrito_id}-{intento}`. | ADR-0013 Fase 1; ADR-0011 C-02; HU-07 crit.1/3 |
| `metodo_entrega = "delivery"` sin `direccion_id` o dirección ajena | HTTP 409/404 según caso; no contacta a Stripe. | **decisión propuesta** |
| `metodo_entrega = "retiro"` | `direccion_id` se ignora; entrega en botica. | **decisión propuesta** |
| Carrito vacío | HTTP 409; `"El carrito está vacío"`. | **decisión propuesta** |
| Carrito con `requiere_receta` sin receta validada | HTTP 409; `"Debes adjuntar y validar tu receta médica para continuar con el pago"`. | W-03 (ADR-0008); CONTRATO-HU-06 |
| Stock insuficiente al reservar | HTTP 409; `"Stock máximo disponible alcanzado (N unidades)"`; no contacta a Stripe. | HU-05; ADR-0012 |

La respuesta nunca incluye datos de tarjeta. Solo se persisten identificadores de Stripe (`payment_intent_id`) y la clave de idempotencia.

### Webhook de confirmación (éxito)

**Entrada**

```http
POST /api/v1/pagos/webhook
Header: Stripe-Signature
```

| Caso | Salida esperada | Origen |
|---|---|---|
| `payment_intent.succeeded`, firma válida, primera vez | HTTP 200; en una transacción MySQL corta: convierte la reserva en decremento definitivo (`confirm_deduction_batch`), crea `Pedido` estado `Registrado` con número único (con `usuario_id`, `direccion_id`, `zona_id`, `metodo_entrega`), crea `Pago` (referencia Stripe + clave de idempotencia) y marca el carrito `completado`. | ADR-0013 Fase 2; HU-07 crit.3; ADR-0012; ADR-0003 |
| `payment_intent.succeeded` duplicado | HTTP 200 sin reprocesar; no se crea segundo `Pedido` ni se descuenta stock dos veces. | ADR-0013; ADR-0007 |
| Firma inválida / ausente | HTTP 400; no procesa. | ADR-0013 |
| Inconsistencia física al confirmar | HTTP 200; `Pedido` se crea en estado `incidencia_stock` (no `Registrado`). | ADR-0013 C-02; TECH-DESIGN L114 |

El webhook responde rápido; `pedido.confirmado` y `despacho.organizar` se publican según ADR-0007 (best-effort, no bloquean el resultado del pago).

### Webhook de pago rechazado

| Caso | Salida esperada | Origen |
|---|---|---|
| `payment_intent.payment_failed` | HTTP 200; **no** crea `Pedido` ni descuenta stock; carrito vuelve de `en_pago` a `activo`; las reservas se liberan de inmediato; los productos permanecen en el carrito para reintentar. | ADR-0013; HU-07 crit.4 |
| Fondos insuficientes | El frontend muestra `"Su pago fue rechazado por saldo insuficiente. Por favor intente con otra tarjeta"`. | HU-07 esc.2 |
| Otra causa de rechazo | El frontend muestra `"El pago no pudo procesarse. Por favor intente con otra tarjeta"`. | **decisión propuesta** (HU-07 crit.4) |

### Estado del pago (polling del frontend)

**Entrada**

```http
GET /api/v1/pagos/{payment_intent_id}
```

| Caso | Salida esperada | Origen |
|---|---|---|
| Pago en proceso | HTTP 200; `{ estado:"procesando", pedido:null }`. | ADR-0013 consecuencia |
| Pago confirmado | HTTP 200; `{ estado:"confirmado", pedido:{ numero, estado, monto, moneda } }`. | **decisión propuesta** |
| Pago rechazado | HTTP 200; `{ estado:"rechazado", pedido:null }`. | **decisión propuesta** |
| `payment_intent_id` desconocido o de otro usuario | HTTP 404. | **decisión propuesta** |

### Consulta de pedido

**Entrada**

```http
GET /api/v1/pedidos/{numero_pedido}
```

| Caso | Salida esperada | Origen |
|---|---|---|
| Pedido propio | HTTP 200; `{ numero, estado, items:[{ producto_id, nombre, cantidad, precio_unitario, subtotal }], monto, moneda, metodo_entrega, entrega }`. | **decisión propuesta**; ADR-0003 |
| Pedido inexistente o de otro usuario | HTTP 404. | **decisión propuesta** |

### Pantalla `/checkout` y confirmación

- `/checkout` requiere sesión autenticada; el guest que llega aquí inicia el checkout (reserva) y es redirigido a iniciar sesión para pagar.
- Captura de entrega: elegir zona, dirección existente o crear una; método `delivery` o `retiro`.
- La captura de número de tarjeta, expiración y CVC ocurre **solo** en Stripe Elements. Botón `Pagar ahora`.
- Tras confirmar en Stripe, la pantalla muestra `Procesando pago...` y sondea `GET /api/v1/pagos/{payment_intent_id}` hasta `confirmado` o `rechazado`.
- Éxito: redirige a la confirmación mostrando `#BL-####`, el resumen de compra y el monto pagado (`S/ x.xx`).
- Rechazo: permanece en `/checkout` con el carrito intacto y muestra el mensaje exacto correspondiente.
- Una vez confirmado el pago no se ofrece ninguna acción de extorno/reembolso (ni cliente ni operador). | HU-07 crit.2/3/4/5

## Nombres que no se negocian

| Tipo | Valor exacto |
|---|---|
| GET | `/api/v1/zonas` |
| GET / POST | `/api/v1/direcciones` |
| POST | `/api/v1/checkout` |
| POST | `/api/v1/pagos/webhook` |
| GET | `/api/v1/pagos/{payment_intent_id}` |
| GET | `/api/v1/pedidos/{numero_pedido}` |
| Body checkout | `direccion_id`, `metodo_entrega` ∈ `delivery` \| `retiro` |
| Body dirección | `direccion_linea1`, `referencia`, `telefono_contacto`, `zona_id` |
| Campo respuesta checkout (guest) | `requiere_autenticacion`, `reserva_expira_en` |
| Campo respuesta checkout (auth) | `payment_intent_id`, `client_secret`, `monto`, `moneda`, `reserva_expira_en` |
| Campo estado pago | `estado` ∈ `procesando` \| `confirmado` \| `rechazado`, `pedido` |
| Cabecera webhook | `Stripe-Signature` |
| Eventos Stripe | `payment_intent.succeeded`, `payment_intent.payment_failed` |
| Estado inicial del pedido | `Registrado` |
| Estado de contingencia | `incidencia_stock` |
| Clave de idempotencia | `pedido-{carrito_id}-{intento}` |
| Formato número de pedido | `BL-<secuencia>`; en UI `#BL-<secuencia>` (ej. `#BL-10045`) |
| Moneda | `PEN`, montos `S/ x.xx` |
| Botón | `Pagar ahora` |
| Mensaje rechazo (fondos) | `Su pago fue rechazado por saldo insuficiente. Por favor intente con otra tarjeta` |
| Mensaje rechazo (otro) | `El pago no pudo procesarse. Por favor intente con otra tarjeta` |
| Mensaje carrito vacío | `El carrito está vacío` |
| Mensaje zona inválida | `Zona no disponible` |
| Estado intermedio UI | `Procesando pago...` |

## Rutas de cada rol

| Rol | Rutas | Origen |
|---|---|---|
| TESTER | `backend/tests/**`, `frontend/tests/**`, `frontend/src/**/*.test.tsx`, `frontend/src/**/*.spec.ts` | `AGENTS.md` |
| DEV | `backend/src/**`, `backend/alembic/**`, `backend/requirements*`, `backend/pyproject.toml`, `backend/.env.example`, `backend/web.config`, `frontend/src/**` (excepto tests), `frontend/package*.json`, `infra/**` | `AGENTS.md` |
| LEAD/humano | `contratos/**`, `informes/**`, `AGENTS.md`, `docs/**` | `AGENTS.md` |

## Avisos de contexto

- HU-05 implementó `POST /api/v1/checkout` **solo para reservar** (guest). HU-07 **cambia** el caso autenticado (ahora devuelve `payment_intent_id`/`client_secret`) y **conserva** el caso guest (reserva + `requiere_autenticacion`). No debe romper los casos verdes de HU-05.
- El pago exige autenticación (decisión humana 2026-11-25): el guest solo reserva y luego inicia sesión.
- La captura de entrega entra en HU-07 (decisión humana 2026-11-25): nuevas tablas `Zona` y `Direccion` + endpoints de §Captura de entrega; se requiere seed de zonas.
- Nuevas tablas de pedido/pago: `Pedido`, `PedidoItem`, `Pago` (migración Alembic nueva), más `Zona` y `Direccion`.
- El SDK de Stripe **no** está en `backend/requirements.txt` (solo `httpx`); el DEV debe añadirlo o invocar la API por HTTP.
- La CSP de `backend/web.config` debe autorizar `https://js.stripe.com`, `https://hooks.stripe.com` y `https://api.stripe.com` (ADR-0019 C-01).
- El ERP no participa en el MVP; `confirm_deduction_batch` usa `LocalMySQLInventoryProvider` dentro del `COMMIT` del pedido (ADR-0012).
- Semántica de totales fijada en HU-05: `subtotal = suma(precio_regular*cantidad)`, `ahorro_total`, `total = subtotal - ahorro_total`. El monto cobrado es `total`.
- Nunca loguear ni persistir número de tarjeta, CVC ni secretos; solo identificadores de Stripe.

## Decisiones propuestas (no venían en la tarea)

| # | Decisión | Por qué hace falta | Estado |
|---|---|---|---|
| 1 | Rutas y campos de §Nombres | La HU no fija endpoints ni campos. | Aprobada por humano (2026-11-25) |
| 2 | Códigos 409/400/404/401 según §Comportamiento; pedidos/pagos ajenos → 404 | La HU no fija estos códigos. | Aprobada por humano (2026-11-25) |
| 3 | Número de pedido `BL-<secuencia>` (UI `#BL-...`) | La HU solo muestra `#BL-10045`. | Aprobada por humano (2026-11-25) |
| 4 | `GET /api/v1/pagos/{payment_intent_id}` para polling `Procesando pago...` | ADR-0013 exige confirmación asíncrona sin fijar endpoint. | Aprobada por humano (2026-11-25) |
| 5 | `payment_failed` libera reservas de inmediato y conserva ítems en el carrito | ADR-0013 y HU-07 combinan ambas reglas. | Aprobada por humano (2026-11-25) |
| 6 | El pago exige autenticación; guest solo reserva y debe iniciar sesión | La HU no aclara si el guest paga; decisión humana. | Aprobada por humano (2026-11-25) |
| 7 | Mensaje genérico de rechazo distinto de fondos insuficientes | HU crit.4 pide mensaje claro para otros rechazos. | Aprobada por humano (2026-11-25) |
| 8 | Bloqueo por receta (W-03) se difiere a HU-06 | El mecanismo de adjuntar receta es HU-06. | Aprobada por humano (2026-11-25) |
| 9 | Eventos `pedido.confirmado`/`despacho.organizar` best-effort | ADR-0013/0007 los exigen; consumidores son HU-08. | Aprobada por humano (2026-11-25) |
| 10 | Captura de entrega en HU-07: `GET /zonas`, `GET|POST /direcciones`, `direccion_id`/`metodo_entrega` en checkout | ADR-0003 exige dirección/zona/entrega en el `Pedido`. | Aprobada por humano (2026-11-25) |
| 11 | `incidencia_stock` se acepta como NO VERIFICADO en caja negra y se cubre con prueba de integración | Provocar inconsistencia física es inviable en E2E. | Aprobada por humano (2026-11-25) |

## Fuera del contrato (decide el DEV)

- Estructura interna de los módulos de pagos/pedidos/direcciones, nombres de funciones y repositorios.
- Uso del SDK `stripe` o llamadas HTTP directas, siempre con verificación de firma del webhook.
- Detalle del esquema de `Zona`/`Direccion`/`Pedido`/`PedidoItem`/`Pago` (respetando ADR-0003) y de la migración Alembic.
- Seed concreto de zonas (mínimo 1 zona activa para la demo).
- Estilos visuales más allá de textos, controles y flujo fijados.
- Estrategia concreta de polling (intervalo, reintentos) mientras respete el estado `Procesando pago...`.

## Preguntas abiertas para el humano

Ninguna. Las decisiones 1–11 quedaron aprobadas por el usuario humano el 2026-11-25.

## Changelog

| Versión | Fecha | Cambio | Motivo | Aprobado por |
|---|---|---|---|---|
| v1 | 2026-11-25 | Versión inicial; pago solo autenticado y captura de entrega en HU-07 | Inicio de HU-07 y respuestas del humano | Usuario humano |
| v2 | 2026-11-27 | Añade bloqueo por receta (W-03) al checkout autenticado | HU-06 implementa W-03 diferido | Usuario humano |
