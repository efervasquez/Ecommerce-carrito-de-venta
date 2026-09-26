# HU-12: Despacho, cobro y entrega física del pedido

## Historia de usuario
Como Farmacéutico  
Quiero gestionar los pedidos en la bandeja Pendientes de entrega, coordinar telefónicamente con el delivery externo o cobrar en mostrador, y marcar la orden como Entregada  
Para formalizar la recepción por parte del cliente, registrar el cobro en efectivo y descontar definitivamente el inventario  

## Alcance específico de la HU
- **Sección del PRD:** 2. Actores (Delivery externo), 3. Alcance — Incluye (Farmacéutico: Marcado de entrega, Despacho, Cobro de efectivo en mostrador o vía delivery telefónico, Registro de `Pagado`), 3. Bandejas (`Pendientes de entrega`, `Entregados`), 4. Estados (`Pendiente de entrega`, `Entregado`).
- **Criterios de éxito asociados:** Criterio 6 (*El stock se descuenta al validar el pago...*), Criterio 8 (*El farmacéutico puede... marcar la entrega*), Criterio 11 (*El cliente recibe notificaciones por los cambios de estado...*).
- **Cobertura:** Visualización de pedidos listos en bandeja `Pendientes de entrega` (con transferencia ya pagada o efectivo pendiente de cobro); entrega en mostrador con cobro de efectivo y pase a `Entregado`; entrega a domicilio con recojo del delivery externo, recepción de llamada de confirmación del delivery tras cobrar al cliente, registro de condición `Pagado`, pase al estado `Entregado` y descuento formal de stock.

## Criterios de aceptación funcionales
1. **Bandeja Pendientes de entrega:** Agrupa todos los pedidos completamente preparados, diferenciando claramente:
   - Pedidos ya pagados (por transferencia).
   - Pedidos con cobro en efectivo pendiente (retiro en tienda o entrega a domicilio).
2. **Flujo de Retiro en tienda con efectivo:**
   - Cuando el cliente acude a la farmacia, el farmacéutico cobra el monto en efectivo en mostrador.
   - El farmacéutico registra la condición de `Pagado` y marca el pedido como `Entregado`.
   - El sistema descuenta definitivamente el stock del inventario.
3. **Flujo de Retiro en tienda con transferencia previa:**
   - Como el pedido ya tiene la condición de `Pagado`, el farmacéutico únicamente verifica la identidad del cliente, entrega el paquete y marca el pedido como `Entregado`.
4. **Flujo de Entrega a domicilio con pago contra entrega (Efectivo):**
   - El repartidor externo retira el paquete de la farmacia.
   - Tras cobrar al cliente y entregarle el paquete, el repartidor llama telefónicamente al farmacéutico para confirmar la entrega y el cobro.
   - Con la confirmación telefónica, el farmacéutico ingresa al sistema, valida el pago marcando la condición `Pagado`, descuenta definitivamente el stock y cambia el pedido a `Entregado`.
5. **Transición y Notificación:** Al marcar un pedido como `Entregado`, el pedido se traslada a la bandeja `Entregados`, sale de las bandejas operativas pendientes y se envía la notificación correspondiente al cliente por su canal principal.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Entrega a domicilio con cobro contra entrega confirmado telefónicamente
```gherkin
Feature: Despacho y entrega de pedidos
  Scenario: Farmacéutico recibe llamada del delivery y marca el pedido como entregado y pagado
    Given que el pedido "PED-801" está en "Pendientes de entrega" con modalidad a domicilio y pago en efectivo pendiente
    When el repartidor externo llama telefónicamente a la farmacia confirmando que el cliente recibió el paquete y pagó en efectivo
    And el farmacéutico registra la condición de "Pagado" y marca el pedido como "Entregado"
    Then el pedido cambia a estado "Entregado" y se traslada a la bandeja "Entregados"
    And el sistema descuenta definitivamente del inventario el stock que estaba reservado
    And se envía una notificación de pedido entregado al canal del cliente
```

### Escenario 2 — Camino feliz: Retiro en tienda de pedido previamente pagado por transferencia
```gherkin
Feature: Despacho y entrega de pedidos
  Scenario: Farmacéutico entrega en mostrador un pedido ya pagado
    Given que el pedido "PED-802" está en "Pendientes de entrega" con condición "Pagado" y modalidad "Retiro en tienda"
    When el cliente se presenta a retirar su compra y el farmacéutico marca "Entregado"
    Then el pedido pasa a la bandeja "Entregados"
    And se envía la notificación de confirmación de entrega al cliente
```

### Escenario 3 — Caso borde: Intento de marcar Entregado en pedido con efectivo sin registrar el cobro
```gherkin
Feature: Despacho y entrega de pedidos
  Scenario: Farmacéutico intenta finalizar una entrega con efectivo pendiente sin validar el pago
    Given que el pedido "PED-803" tiene pago en efectivo pendiente en "Pendientes de entrega"
    When el farmacéutico intenta marcar "Entregado" sin registrar la recepción del efectivo
    Then el sistema solicita obligatoriamente confirmar el cobro del dinero antes de pasar a "Entregado"
```

## Puntos Abiertos
- Sin puntos abiertos pendientes. Todas las definiciones fueron confirmadas en el PRD.

## Exclusiones ("No incluye")
- Pasarela de pago en línea (fuera de alcance en Sección 5 del PRD).
- App móvil o interfaz web para el motorizado de delivery (el delivery externo no interactúa con el sistema según Sección 2 y 5).
- Cobro con datáfono inalámbrico integrado a la PWA durante el delivery.
