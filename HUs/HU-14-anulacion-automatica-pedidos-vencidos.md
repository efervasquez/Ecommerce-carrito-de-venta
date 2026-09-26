# HU-14: Anulación automática de pedidos con más de 24 horas en Pedidos recibidos

## Historia de usuario
Como Sistema automatizado de la farmacia  
Quiero anular de forma automática los pedidos que permanezcan más de 24 horas en la bandeja Pedidos recibidos desde su creación  
Para evitar el bloqueo indefinido de inventario y liberar el stock reservado de pedidos no procesados  

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance — Incluye (Farmacéutico: Anulación automática por más de 24 horas en Pedidos recibidos, Liberación de stock, Excepción expresa), 4. Estados (`Anulado`), 6. Criterios de éxito (Criterio 13).
- **Criterios de éxito asociados:** Criterio 6 (*...se libera cuando un pedido o medicamento se anula*), Criterio 11 (*El cliente recibe notificaciones por... anulaciones...*), Criterio 13 (*Los pedidos que permanecen en Pedidos recibidos durante más de 24 horas desde su generación se anulan automáticamente y liberan el stock reservado. Esta regla no aplica a pedidos En preparación ni Pendientes de entrega*).
- **Cobertura:** Proceso en segundo plano (job/tarea programada) que evalúa los pedidos en estado `Recibido` (bandeja `Pedidos recibidos`); cálculo determinista del tiempo transcurrido desde la creación (timestamp de generación); anulación automática al superar 24 horas continuas; transición a estado `Anulado` y bandeja `Pedidos anulados`; liberación inmediata de la reserva de stock; notificación al cliente; exclusión estricta de cualquier pedido que se encuentre en preparación o pendiente de entrega.

## Criterios de aceptación funcionales
1. **Regla de tiempo determinista:** El sistema evalúa periódicamente todos los pedidos ubicados en la bandeja `Pedidos recibidos`. Si el tiempo transcurrido desde la fecha y hora de generación del pedido supera las 24 horas continuas (24 horas y 0 minutos), el sistema lo anula de manera automática.
2. **Liberación de reserva de stock:** Al ejecutarse la anulación automática, el sistema libera inmediatamente todo el stock retenido en reserva para ese pedido, poniéndolo a disposición de otros clientes en el catálogo.
3. **Cambio de estado y bandeja:** El pedido cambia a estado `Anulado` y se almacena en la bandeja `Pedidos anulados` del farmacéutico con el motivo "Expiración de tiempo límite de validación (más de 24 horas)".
4. **Exclusión estricta de estados avanzados:** La anulación automática aplica **única y exclusivamente** a pedidos en la bandeja `Pedidos recibidos`. Bajo ninguna circunstancia debe afectar ni anular pedidos que se encuentren en `En preparación` o `Pendientes de entrega`, incluso si superan las 24 horas desde su generación.
5. **Notificación al cliente:** El sistema envía una notificación automática al cliente por su canal principal configurado informándole que su pedido fue anulado por no haberse completado el proceso de validación o pago en el plazo de 24 horas.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Pedido supera las 24 horas en Pedidos recibidos y se anula automáticamente
```gherkin
Feature: Anulación automática de pedidos vencidos
  Scenario: Sistema anula un pedido que cumplió más de 24 horas en Pedidos recibidos
    Given que el pedido "PED-1001" fue generado hace 24 horas y 15 minutos y permanece en la bandeja "Pedidos recibidos"
    When el proceso automático de control de vencimiento se ejecuta
    Then el sistema cambia el estado de "PED-1001" a "Anulado"
    And lo traslada a la bandeja "Pedidos anulados"
    And libera inmediatamente todas las unidades de stock que tenía reservadas
    And envía una notificación al cliente informando la anulación automática del pedido
```

### Escenario 2 — Caso borde: Pedido con 23 horas y 50 minutos no se anula
```gherkin
Feature: Anulación automática de pedidos vencidos
  Scenario: Pedido cercano al límite permanece activo en Pedidos recibidos
    Given que el pedido "PED-1002" fue generado hace 23 horas y 50 minutos y está en la bandeja "Pedidos recibidos"
    When el proceso automático de control evalúa el pedido
    Then el sistema mantiene el pedido "PED-1002" en estado "Recibido"
    And conserva intacta la reserva de stock
```

### Escenario 3 — Caso borde: Pedido en preparación que supera las 24 horas no se anula
```gherkin
Feature: Anulación automática de pedidos vencidos
  Scenario: Pedido en estado En preparación no es afectado por la regla de 24 horas
    Given que el pedido "PED-1003" fue generado hace 26 horas pero se encuentra en la bandeja "En preparación"
    When el proceso automático de vencimiento se ejecuta
    Then el sistema no modifica el estado ni el stock del pedido "PED-1003"
    And el pedido continúa normalmente su flujo en "En preparación"
```

## Puntos Abiertos
- Sin puntos abiertos pendientes. Todas las definiciones fueron confirmadas en el PRD.

## Exclusiones ("No incluye")
- Pasarela de pago en línea (fuera de alcance en Sección 5 del PRD).
- Consideración de feriados o fines de semana (la regla de 24 horas es continua desde la generación según definición aprobada en PRD).
- Prórrogas automáticas solicitadas por el cliente a través de la aplicación.
