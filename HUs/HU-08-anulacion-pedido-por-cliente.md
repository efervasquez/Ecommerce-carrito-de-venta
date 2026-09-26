# HU-08: Anulación de pedido no pagado por el cliente

## Historia de usuario
Como Cliente autenticado  
Quiero anular mi pedido no pagado directamente desde la PWA mientras no haya cambiado de estado o coordinarlo con el farmacéutico si ya avanzó  
Para cancelar compras no deseadas y liberar el stock reservado  

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance — Incluye (Cliente: Anulación de pedidos no pagados desde la PWA), 4. Estados del pedido (`Anulado`), 6. Criterios de éxito (Criterio 12).
- **Criterios de éxito asociados:** Criterio 12 (*El cliente puede anular pedidos no pagados desde la PWA antes de Entregado o Archivado; después debe coordinar con el farmacéutico*), Criterio 6 (*El stock se descuenta al validar el pago y se libera cuando un pedido o medicamento se anula*).
- **Cobertura:** Botón de anulación en la PWA disponible para el cliente en sus pedidos que se encuentren en estado `Recibido` (sin pago confirmado). Liberación inmediata de stock reservado. Mensaje de restricción y orientación de coordinación telefónica con la farmacia si el pedido ya cambió de estado operativo (ej. `En preparación` o `Pendiente de entrega`) o si ya figura como pagado.

## Criterios de aceptación funcionales
1. **Permiso de anulación directa:** El cliente puede anular directamente su pedido desde la PWA siempre que el pedido cumpla las dos condiciones:
   - No esté pagado.
   - Se encuentre en estado `Recibido` antes de entrar a preparación o entrega.
2. **Liberación de stock:** Al confirmar la anulación, el sistema cambia inmediatamente el estado del pedido a `Anulado`, libera el 100% del stock reservado de todos sus ítems y traslada el pedido a la bandeja `Pedidos anulados`.
3. **Notificación de anulación:** El sistema emite una confirmación en pantalla y envía una notificación por el canal principal configurado confirmando que el pedido fue cancelado.
4. **Restricción por cambio de estado:** Si el pedido ya cambió de estado (por ejemplo, pasó a `En preparación` o `Pendiente de entrega` con pago contra entrega), el botón de anulación directa en la PWA se deshabilita o muestra un mensaje informando que debe comunicarse telefónicamente con la farmacia para coordinar la anulación.
5. **Bloqueo para pedidos pagados:** Si el pedido ya tiene condición de `Pagado`, el cliente no puede anularlo desde la PWA bajo ninguna circunstancia (los pedidos pagados y no entregados solo pueden archivarse por la farmacia).

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Cliente anula pedido no pagado en estado Recibido
```gherkin
Feature: Anulación de pedido por cliente
  Scenario: Cliente anula con éxito un pedido no pagado desde la PWA
    Given que el cliente tiene el pedido "PED-401" en estado "Recibido" con pago en efectivo pendiente
    When el cliente ingresa al detalle del pedido en la PWA y presiona "Anular pedido"
    And confirma la acción en el diálogo de advertencia
    Then el sistema actualiza el estado del pedido a "Anulado"
    And libera inmediatamente todo el stock que estaba reservado para ese pedido
    And envía una notificación de anulación al canal principal del cliente
```

### Escenario 2 — Caso borde: Cliente intenta anular un pedido que ya cambió a En preparación
```gherkin
Feature: Anulación de pedido por cliente
  Scenario: Cliente intenta anular un pedido que ya está en preparación
    Given que el pedido "PED-402" del cliente avanzó al estado "En preparación"
    When el cliente visualiza el detalle del pedido en la PWA
    Then el botón de anulación directa no está disponible
    And el sistema muestra el mensaje: "El pedido ya se encuentra en preparación. Si desea cancelarlo, por favor comuníquese telefónicamente con la farmacia para coordinar con el farmacéutico"
```

### Escenario 3 — Caso borde: Intento de anular un pedido con pago ya registrado
```gherkin
Feature: Anulación de pedido por cliente
  Scenario: Cliente intenta anular un pedido que ya tiene validado el pago
    Given que el pedido "PED-403" tiene el estado de pago "Pagado"
    When el cliente revisa su pedido en la PWA
    Then el sistema no permite anular el pedido
    And no muestra la opción de anulación para pedidos pagados
```

## Puntos Abiertos
- Sin puntos abiertos pendientes. Todas las definiciones fueron confirmadas en el PRD.

## Exclusiones ("No incluye")
- Pasarela de pago en línea (fuera de alcance en Sección 5 del PRD).
- Reembolso automático de fondos en caso de cancelaciones (las diferencias de pedidos pagados se gestionan en farmacia).
- Cancelación automática de pedidos una vez entregados (estado terminal).
