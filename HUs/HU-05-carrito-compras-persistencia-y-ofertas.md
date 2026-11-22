# HU-05: Carrito de compras con persistencia ligada a sesión, reserva de stock de 24 horas y visualización prioritaria de ofertas

## Historia de usuario
Como Cliente Final  
Quiero que mi carrito de compras conserve los productos seleccionados durante mi sesión activa con una reserva de inventario vigente por 24 horas y despliegue prioritariamente en la parte superior aquellos productos que tengan ofertas activas  
Para no perder mi selección ni la disponibilidad reservada mientras navego, y aprovechar de forma clara las promociones vigentes antes de proceder al pago.

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance (3.1 Lo que INCLUYE — Carrito de Compras con Persistencia e Interfaz Orientada a Ofertas), 4. Personas y Actores (Cliente Final), 5. Requerimientos Funcionales (RF-03: Automatización OCR y Carrito de Compras — RF-03.3, RF-03.4, RF-03.5, RF-03.6).
- **Requerimientos Funcionales asociados:**
  - RF-03.3 (*El sistema ordenará la interfaz del carrito de compras colocando todos los productos que tengan ofertas activas en la sección superior inicial de la pantalla*).
  - RF-03.4 (*El carrito mantendrá la reserva de inventario vinculada a la sesión por un lapso de 24 horas; al transcurrir dicho tiempo sin formalizar el pago, el sistema liberará automáticamente la reserva devolviendo las existencias al catálogo*).
  - RF-03.5 (*La reserva de stock se regirá por el tipo de sesión: el invitado [guest] reservará únicamente al iniciar el checkout, mientras que el autenticado reservará al agregar productos al carrito; en ambos casos la reserva expira a las 24 horas — PA-06*).
  - RF-03.6 (*Límites anti-abuso de reserva: 3 unidades por SKU, 10 productos por carrito guest, rate limit de 1 req/s con burst 5 al agregar, 3 inicios de checkout por minuto por IP y techo de 1 checkout guest activo con reservas [o máx. 15 unidades] por IP — PA-07*).
  - La persistencia y reserva de productos ligada a la sesión proviene además de la Sección 3.1 del PRD (*Selección y reserva de productos ligada a la sesión del cliente con una vigencia máxima de 24 horas — PA-01*).
- **Criterios de éxito y RNF asociados:** RNF-01 (*Tiempo de respuesta <= 2.5s en procesamiento de carritos bajo carga sostenida de 250 clientes concurrentes*), Criterio de éxito — Penetración Digital (*Al menos el 25% de la facturación global proveniente del canal de ventas web según Sección 8 del PRD*), AGENTS.md (*Optimización de recursos y pool de conexiones en MySQL; tareas programadas de ciclo de vida para carritos*).
- **Cobertura:** Almacenamiento y persistencia del estado del carrito ligado al token/sesión del cliente, ordenamiento obligatorio de la interfaz con bloque superior prioritario para productos con ofertas, sección secundaria para productos regulares, actualización interactiva de cantidades, cálculo de totales y reserva temporal de inventario.

## Criterios de aceptación funcionales
1. **Persistencia del carrito ligada a la sesión:**
   - Todo producto agregado se almacena en el carrito vinculado a la sesión activa del cliente.
   - Si el usuario refresca el navegador, cambia de página en el catálogo o ingresa a la vista de detalle de un producto, el contenido de su carrito se mantiene intacto.
2. **Sección prioritaria de ofertas en el carrito:**
   - Al abrir la vista del carrito de compras, la pantalla debe desplegar de forma obligatoria y en la parte superior inicial una sección destacada con todos los productos que posean ofertas y descuentos porcentuales activos.
   - En este bloque se muestra claramente el precio original tachado, el porcentaje de descuento y el precio final con descuento.
3. **Sección de productos a precio regular:**
   - Debajo del bloque prioritario de ofertas, el carrito lista los productos convencionales que no tienen descuento activo.
4. **Modificación de cantidades y recálculo interactivo:**
   - El cliente puede incrementar o reducir las unidades de cualquier producto en el carrito, o eliminarlo mediante un botón de supresión.
   - El sistema valida que las unidades solicitadas no excedan el stock disponible.
   - La interfaz recalcula en tiempo real los subtotales por producto, el total de ahorro por descuentos y el importe final a pagar.
5. **Reserva de stock con vigencia de 24 horas:**
   - La reserva temporal de inventario tiene una vigencia máxima de 24 horas y se libera automáticamente al expirar sin concretar el pago (inactividad/timeout), devolviendo las unidades al stock disponible del catálogo (PA-01).
   - **Regla de reserva por tipo de sesión (PA-06 / RF-03.5):**
     - **Cliente autenticado:** reserva stock en el momento de agregar cada producto al carrito.
     - **Cliente invitado (guest):** no reserva al agregar; reserva recién al iniciar el checkout.
     - En ambos casos el TTL es de 24 horas con liberación automática.
6. **Límites anti-abuso de cara al cliente (PA-07 / RF-03.6):**
   - Máximo **3 unidades por SKU** dentro de un mismo carrito.
   - Máximo **10 productos distintos por carrito guest**.
   - El sistema bloquea cualquier intento que supere estos límites y muestra un mensaje claro al cliente.
7. **Control de tasa al agregar al carrito (PA-07 / RF-03.6):**
   - La adición de productos al carrito está limitada a **1 petición por segundo con burst de 5**. Al excederlo, el sistema rechaza la petición con un aviso de reintento.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Visualización prioritaria de productos en oferta en el encabezado del carrito
```gherkin
Feature: Carrito de compras con persistencia y ofertas
  Scenario: Cliente abre el carrito que contiene productos regulares y productos con oferta
    Given que el cliente tiene en su carrito 1 "Paracetamol 500mg" (precio regular S/ 5.00)
    And 1 "Protector Solar SPF 50+" con oferta activa del 20% de descuento (precio original S/ 50.00, con descuento S/ 40.00)
    When el cliente ingresa a la vista del carrito de compras
    Then el sistema renderiza en la parte superior inicial la sección prioritaria de "Productos en Oferta"
    And exhibe en dicha sección el "Protector Solar SPF 50+" indicando "20% DSCTO" y precio de "S/ 40.00"
    And renderiza en la parte inferior los demás productos regulares incluyendo "Paracetamol 500mg"
    And muestra el total consolidado a pagar por "S/ 45.00" y un ahorro de "S/ 10.00"
```

### Escenario 2 — Caso borde: Modificación de cantidad superando el stock disponible del producto
```gherkin
Feature: Carrito de compras con persistencia y ofertas
  Scenario: Cliente intenta incrementar la cantidad de un producto más allá de las existencias reales
    Given que el producto "Jarabe Antitusígeno 120ml" tiene un stock disponible de 4 unidades
    And el cliente tiene actualmente 4 unidades de dicho jarabe en su carrito de compras
    When el cliente pulsa el botón "+" para solicitar una 5ta unidad
    Then el sistema bloquea el incremento
    And mantiene la cantidad en 4 unidades
    And muestra un mensaje de advertencia indicando "Stock máximo disponible alcanzado (4 unidades)"
```

### Escenario 3 — Caso borde: Expiración de la reserva de stock a las 24 horas y liberación automática
```gherkin
Feature: Carrito de compras con persistencia y ofertas
  Scenario: La reserva de inventario expira a las 24 horas sin pago y libera el stock
    Given que el cliente reservó 1 unidad de "Omeprazol 20mg" en su carrito hace 24 horas
    And no ha formalizado el pago de la orden
    When el sistema ejecuta el proceso programado de expiración de reservas
    Then libera automáticamente la unidad reservada devolviéndola al stock disponible del catálogo
    And el cliente ya no cuenta con la disponibilidad asegurada de esa unidad al intentar continuar con el pago
```

### Escenario 4 — Caso borde: El cliente invitado (guest) no reserva stock al agregar, sino recién al iniciar el checkout
```gherkin
Feature: Carrito de compras con persistencia y ofertas
  Scenario: Guest agrega productos sin reservar stock hasta llegar al checkout
    Given que un cliente invitado (guest) navega sin haber iniciado sesión
    When agrega 1 unidad de "Paracetamol 500mg" al carrito
    Then el sistema registra el producto en el carrito del guest
    And no genera reserva de stock sobre "Paracetamol 500mg" en ese momento
    When el guest inicia el checkout
    Then el sistema genera la reserva de stock de los productos del carrito con vigencia de 24 horas
```

### Escenario 5 — Caso borde: Intento de superar el límite de 3 unidades por SKU en el carrito
```gherkin
Feature: Carrito de compras con persistencia y ofertas
  Scenario: Cliente intenta agregar más de 3 unidades de un mismo producto
    Given que el cliente ya tiene 3 unidades de "Ibuprofeno 400mg" en su carrito
    When intenta agregar una 4ta unidad del mismo SKU
    Then el sistema bloquea la adición
    And mantiene la cantidad en 3 unidades
    And muestra un mensaje indicando "Límite máximo de 3 unidades por producto"
```

## Supuestos
- **Mecanismo de reserva temporal:** Confirmado por PA-01 (31/10/2026): la reserva temporal de stock opera asociada al identificador de sesión activa del cliente mediante transacciones atómicas a nivel de base de datos para prevenir sobreventa concurrente, con vigencia máxima de 24 horas y liberación automática por timeout/expiración o inactividad.
- **Reserva por tipo de sesión (PA-06):** Confirmado el 31/10/2026 — el guest reserva solo al iniciar el checkout y el autenticado al agregar. Se asume que la sesión guest se identifica mediante token/cookie de sesión anónima.
- **Controles anti-abuso (PA-07):** Confirmado el 31/10/2026 — los límites (3 unidades/SKU, 10 productos/guest, rate limit 1 req/s con burst 5) se aplican en el backend y son verificables por el tester.

## Puntos Abiertos (Resueltos)
- **PA-01 — Reserva de stock:** RESUELTO (31/10/2026). La reserva de stock queda establecida en **24 horas**. Transcurrido este lapso sin concretar la compra o por inactividad/timeout, el sistema libera automáticamente las unidades reservadas devolviéndolas al stock disponible.
- **PA-06 — Reserva de stock por tipo de sesión:** RESUELTO (31/10/2026). El cliente **invitado (guest)** reserva solo al iniciar el checkout; el **autenticado** reserva al agregar al carrito; ambos con TTL de 24 horas (RF-03.5).
- **PA-07 — Parámetros anti-abuso de reserva:** RESUELTO (31/10/2026). 3 unidades por SKU, 10 productos por carrito guest, rate limit de 1 req/s con burst 5 al agregar, 3 inicios de checkout por minuto por IP y techo de 1 checkout guest activo con reservas (o máx. 15 unidades) por IP (RF-03.6).

## Exclusiones ("No incluye")
- Cupones de descuento promocionales manuales o códigos alfanuméricos ingresados por el usuario (no contemplado en el PRD).
- Devolución de dinero en efectivo o extornos tras concretar el pago (política estricta de no reembolso de la Sección 3.2).
- Aplicación Móvil Nativa descargable.
