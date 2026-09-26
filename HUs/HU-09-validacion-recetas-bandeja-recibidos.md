# HU-09: Validación de recetas médicas en bandeja Pedidos recibidos

## Historia de usuario
Como Farmacéutico  
Quiero identificar en la bandeja Pedidos recibidos las órdenes con recetas médicas adjuntas y aprobarlas o rechazarlas  
Para garantizar el despacho legal de medicamentos bajo prescripción y actualizar el pedido y su stock adecuadamente  

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance — Incluye (Farmacéutico: Visualización de bandejas, Identificación visual en Pedidos recibidos, Validación de receta, Aprobación y rechazo, Eliminación de medicamento y recálculo, Notificación de rechazo y resolución de dinero en transferencias, Anulación de pedido de un solo medicamento).
- **Criterios de éxito asociados:** Criterio 3 (*Los pedidos con medicamentos que requieren receta permanecen en Recibido, dentro de la bandeja Pedidos recibidos, y muestran una marca visual diferenciada para el farmacéutico*), Criterio 4 (*Todo pedido con receta adjunta pasa por validación de receta y pago antes de entrar en preparación...*), Criterio 6 (*...se libera cuando un pedido o medicamento se anula*).
- **Cobertura:** Visualización en bandeja `Pedidos recibidos` con indicador gráfico/distintivo para pedidos con recetas adjuntas; visor de imagen de la receta médica (JPG, PNG o GIF); acciones de aprobar o rechazar receta por medicamento; flujo de rechazo en pedido multi-producto (eliminación del ítem, recálculo del total, liberación de stock, notificación al cliente y advertencia de resolución manual de dinero en farmacia si fue pagado por transferencia); flujo de rechazo en pedido de único producto (transición automática a `Anulado`, liberación de stock y notificación).

## Criterios de aceptación funcionales
1. **Identificación visual en bandeja:** En la bandeja `Pedidos recibidos`, todo pedido que contenga al menos un medicamento sujeto a receta debe exhibir una marca visual destacada (ej. ícono o badge "Requiere validación de receta").
2. **Visualizador de receta:** El farmacéutico puede abrir e inspeccionar la imagen de la receta médica adjunta por el cliente directamente en la interfaz.
3. **Aprobación de receta:** Al validar que la receta es conforme, el farmacéutico marca la receta como aprobada para el medicamento evaluado.
4. **Rechazo en pedido de múltiples productos:**
   - Si la receta de un medicamento es rechazada: se elimina únicamente ese medicamento del pedido.
   - El stock reservado de ese medicamento se libera inmediatamente al stock disponible.
   - El sistema recalcula automáticamente el monto total del pedido.
   - El pedido continúa su curso normal con los productos restantes aprobados.
   - Se emite una notificación al cliente indicando el medicamento eliminado y el motivo del rechazo.
   - Si el pedido ya había sido pagado por transferencia, la notificación debe informar expresamente que la diferencia de dinero se resolverá manualmente de forma presencial en la farmacia (sin reembolso automático).
   - El cliente no puede agregar otro medicamento de reemplazo en este pedido; si desea otro producto debe crear un nuevo pedido.
5. **Rechazo en pedido de único producto:**
   - Si el pedido contiene un único medicamento y su receta es rechazada: el pedido cambia inmediatamente a estado `Anulado` y se traslada a la bandeja `Pedidos anulados`.
   - Se libera el 100% del stock reservado.
   - Se notifica al cliente la anulación del pedido por receta rechazada y, si pagó por transferencia, que debe acercarse a la farmacia para la resolución manual de su dinero.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Farmacéutico aprueba receta médica válida
```gherkin
Feature: Validación de recetas médicas
  Scenario: Farmacéutico valida y aprueba la receta médica de un pedido
    Given que el pedido "PED-501" se encuentra en la bandeja "Pedidos recibidos" con marca visual de receta requerida
    When el farmacéutico abre el pedido, inspecciona la receta médica adjunta y presiona "Aprobar receta"
    Then el sistema registra la receta como aprobada para ese medicamento
    And el pedido queda habilitado para avanzar a preparación una vez validado el pago correspondiente
```

### Escenario 2 — Caso borde: Rechazo de receta en un pedido con varios medicamentos y pago por transferencia
```gherkin
Feature: Validación de recetas médicas
  Scenario: Farmacéutico rechaza receta de un ítem en pedido multi-producto pagado por transferencia
    Given que el pedido "PED-502" tiene 2 productos: "Amoxicilina" (con receta, S/ 20.00) y "Vitamina C" (S/ 15.00), pagado por transferencia con total de S/ 35.00
    When el farmacéutico rechaza la receta de "Amoxicilina" indicando el motivo "Receta médica vencida"
    Then el sistema elimina la "Amoxicilina" del pedido "PED-502"
    And libera inmediatamente el stock reservado de "Amoxicilina"
    And recalcula el total del pedido a S/ 15.00 manteniendo la "Vitamina C"
    And envía una notificación al cliente informando la eliminación de la "Amoxicilina", el motivo "Receta médica vencida" y que la diferencia económica de S/ 20.00 se resolverá manualmente en la farmacia
```

### Escenario 3 — Caso borde: Rechazo de receta en pedido de un único medicamento
```gherkin
Feature: Validación de recetas médicas
  Scenario: Farmacéutico rechaza la receta del único producto del pedido
    Given que el pedido "PED-503" contiene únicamente 1 unidad de "Azitromicina" en estado "Recibido"
    When el farmacéutico rechaza la receta adjunta
    Then el sistema cambia el estado del pedido "PED-503" a "Anulado"
    And traslada el pedido a la bandeja "Pedidos anulados"
    And libera inmediatamente el stock reservado de "Azitromicina"
    And notifica al cliente la anulación del pedido
```

## Puntos Abiertos
- Sin puntos abiertos pendientes. Todas las definiciones fueron confirmadas en el PRD.

## Exclusiones ("No incluye")
- Pasarela de pago en línea (fuera de alcance en Sección 5 del PRD).
- Edición o adición de medicamentos sustitutos dentro del mismo pedido (excluido expresamente en Sección 3 y 5; requiere un pedido nuevo).
- Reembolsos bancarios automatizados en línea (excluido en Sección 5).
