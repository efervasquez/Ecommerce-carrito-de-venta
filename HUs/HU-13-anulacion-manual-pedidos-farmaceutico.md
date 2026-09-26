# HU-13: Anulación manual de pedidos no pagados por el farmacéutico

## Historia de usuario
Como Farmacéutico  
Quiero anular manualmente un pedido no pagado antes de que pase a Entregado o Archivado  
Para gestionar desestimientos coordinados con el cliente o incidencias operativas, liberando de inmediato el stock reservado  

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance — Incluye (Farmacéutico: Anulación manual de pedidos no pagados, Exclusión de pedidos pagados y no entregados), 3. Bandejas (`Pedidos anulados` visible solo para farmacéutico), 4. Estados (`Anulado`).
- **Criterios de éxito asociados:** Criterio 6 (*...se libera cuando un pedido o medicamento se anula*), Criterio 8 (*El farmacéutico puede... gestionarlos por bandejas...*), Criterio 11 (*El cliente recibe notificaciones por... anulaciones...*).
- **Cobertura:** Opción de anulación manual disponible para el farmacéutico en pedidos no pagados en estados `Recibido`, `En preparación` o `Pendiente de entrega`; validación estricta de que el pedido no tenga condición de `Pagado`; traslado del pedido a la bandeja `Pedidos anulados` (de visualización exclusiva para el farmacéutico); liberación inmediata del 100% del stock reservado y notificación al cliente.

## Criterios de aceptación funcionales
1. **Condición estricta de no pagado:** El farmacéutico solo puede ejecutar la anulación manual si el pedido NO tiene registrada la condición de `Pagado`.
2. **Estados permitidos:** La anulación manual por farmacéutico puede ejecutarse en pedidos no pagados en los estados:
   - `Recibido`.
   - `En preparación` (por ejemplo, pedidos con pago en efectivo donde el cliente cancela telefónicamente).
   - `Pendiente de entrega` (por ejemplo, pedidos con efectivo donde el cliente rechaza la entrega o no es habido por el delivery).
3. **Bloqueo para pedidos pagados:** Si el pedido ya cuenta con la condición de `Pagado`, el sistema bloquea cualquier intento de anulación e indica que los pedidos pagados y no entregados deben trasladarse exclusivamente a `Archivado`.
4. **Liberación de stock:** Al confirmar la anulación, el sistema libera inmediatamente todo el stock que se encontraba reservado para el pedido, restituyéndolo al stock disponible general.
5. **Traslado a bandeja exclusiva:** El pedido pasa al estado `Anulado` y se muestra en la bandeja `Pedidos anulados`, accesible únicamente para el rol de Farmacéutico.
6. **Notificación:** El sistema despacha una notificación al cliente por su canal principal informando la anulación del pedido.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Farmacéutico anula pedido no pagado en preparación
```gherkin
Feature: Anulación manual por farmacéutico
  Scenario: Farmacéutico anula un pedido con efectivo pendiente en preparación tras llamada del cliente
    Given que el pedido "PED-901" no pagado (efectivo) se encuentra en la bandeja "En preparación"
    When el cliente llama solicitando cancelar y el farmacéutico presiona "Anular pedido"
    And confirma la acción ingresando el motivo "Cancelación solicitada por el cliente"
    Then el pedido cambia a estado "Anulado"
    And se traslada a la bandeja "Pedidos anulados"
    And se libera todo el stock reservado de sus productos
    And se envía una notificación de anulación al cliente por su canal principal
```

### Escenario 2 — Caso borde: Intento de anular un pedido pagado y no entregado
```gherkin
Feature: Anulación manual por farmacéutico
  Scenario: Farmacéutico intenta anular un pedido que ya está pagado por transferencia
    Given que el pedido "PED-902" se encuentra en "Pendientes de entrega" con condición "Pagado"
    When el farmacéutico intenta ejecutar la acción de anular el pedido
    Then el sistema bloquea la acción
    And muestra el mensaje de error: "Un pedido pagado no puede ser anulado. Debe registrarse como Archivado según la política operativa"
```

## Puntos Abiertos
- Sin puntos abiertos pendientes. Todas las definiciones fueron confirmadas en el PRD.

## Exclusiones ("No incluye")
- Pasarela de pago en línea (fuera de alcance en Sección 5 del PRD).
- Anulación de pedidos que ya tengan el estado `Entregado` o `Archivado`.
- Bandeja de pedidos anulados visible para otros roles (los clientes solo ven el estado `Anulado` en su historial personal; la bandeja operativa general es exclusiva del farmacéutico).
