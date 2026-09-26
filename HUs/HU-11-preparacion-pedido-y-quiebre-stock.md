# HU-11: Preparación manual de pedidos y gestión de faltante de stock

## Historia de usuario
Como Farmacéutico  
Quiero trasladar pedidos validados a la bandeja En preparación (con color diferenciado si tienen cobro pendiente en efectivo) y gestionar posibles quiebres de stock físicos  
Para armar los paquetes de medicamentos y atender incidencias de inventario de acuerdo con las políticas del negocio  

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance — Incluye (Farmacéutico: Preparación manual, Validación previa de receta y pago, Excepción para efectivo contra entrega a domicilio o retiro en tienda, Manejo de falta de stock físico y notificación, Resolución manual de diferencias en pedidos pagados), 3. Bandejas (`En preparación` con color diferenciado), 4. Estados (`En preparación`), 5. No incluye (*Reemplazo de medicamento por falta de stock*, *Reembolsos automáticos*).
- **Criterios de éxito asociados:** Criterio 4 (*Todo pedido pasa por validación... salvo el pago en efectivo contra entrega...*), Criterio 8 (*El farmacéutico puede... preparar pedidos...*), Criterio 9 (*...color diferenciado en la bandeja En preparación*), Criterio 11 (*El cliente recibe notificaciones por... eliminación de medicamentos*).
- **Cobertura:** Transición de pedidos a la bandeja `En preparación`; visualización con color diferenciado para pedidos con efectivo pendiente de cobro (domicilio o retiro); interfaz de armado físico; procedimiento ante falta de stock físico de un ítem (eliminación individual, liberación de stock restante, recálculo del total, notificación al cliente, indicación de que diferencias económicas se resuelven presencialmente en farmacia y bloqueo de sustitución de producto).

## Criterios de aceptación funcionales
1. **Condiciones de entrada a preparación:**
   - Para pedidos con medio de pago `Transferencia`: deben contar con la receta validada (si aplica) y la condición de `Pagado` registrada.
   - Para pedidos con medio de pago `Efectivo` (contra entrega a domicilio o retiro en tienda): ingresan a preparación una vez validada la receta (si aplica), sin exigir validación de pago previo.
2. **Color diferenciado en bandeja:** En la bandeja `En preparación`, los pedidos con pago pendiente en efectivo (domicilio o retiro en tienda) deben mostrarse visualmente resaltados con un color diferenciado respecto a los pedidos ya pagados por transferencia.
3. **Gestión de faltante de stock físico:** Si durante el armado físico el farmacéutico constata que no hay stock real suficiente de un medicamento:
   - Presiona la opción de reportar faltante para ese medicamento específico.
   - El sistema elimina únicamente ese medicamento del pedido.
   - Si existía alguna unidad reservada en sistema para ese ítem, se libera.
   - El sistema recalcula automáticamente el monto total del pedido con los productos restantes.
   - Se emite una notificación al cliente detallando el medicamento retirado y el motivo (quiebre de stock).
   - El medicamento eliminado no puede reemplazarse dentro del mismo pedido (si el cliente desea otra alternativa, debe generar un nuevo pedido).
4. **Tratamiento del dinero en pedidos pagados:** Si el pedido con faltante ya estaba pagado (por transferencia):
   - No se realiza reembolso automático en el sistema.
   - La notificación al cliente y la interfaz del pedido indican explícitamente que la diferencia económica a favor del cliente se resolverá manualmente de forma presencial en la farmacia.
5. **Finalización de preparación:** Una vez reunidos todos los productos físicos disponibles, el farmacéutico marca el pedido como completado, avanzando a la bandeja `Pendientes de entrega`.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Pedido con pago en efectivo entra a preparación con color diferenciado
```gherkin
Feature: Preparación de pedidos y quiebre de stock
  Scenario: Pedido con retiro en tienda y pago en efectivo entra a la bandeja En preparación
    Given que el pedido "PED-701" tiene aprobadas sus recetas y tiene modalidad "Retiro en tienda" con pago "Efectivo"
    When el pedido avanza al estado "En preparación"
    Then el pedido se muestra dentro de la bandeja "En preparación"
    And exhibe un color visual diferenciado indicando que el pago está pendiente de cobro
```

### Escenario 2 — Caso borde: Faltante físico de stock en un pedido pagado por transferencia
```gherkin
Feature: Preparación de pedidos y quiebre de stock
  Scenario: Farmacéutico detecta falta de stock de un ítem al preparar un pedido pagado
    Given que el pedido "PED-702" pagado por transferencia contiene "Jarabe Tos" (S/ 25.00) y "Gasas" (S/ 10.00), total S/ 35.00
    When el farmacéutico reporta que no hay unidades físicas de "Jarabe Tos"
    Then el sistema elimina "Jarabe Tos" del pedido "PED-702"
    And recalcula el total del pedido a S/ 10.00
    And notifica al cliente que se retiró "Jarabe Tos" por falta de stock y que el saldo a favor de S/ 25.00 se cobrará manualmente en la farmacia
    And el pedido continúa en preparación únicamente con las "Gasas" sin permitir agregar otro producto en su reemplazo
```

## Puntos Abiertos
- Sin puntos abiertos pendientes. Todas las definiciones fueron confirmadas en el PRD.

## Exclusiones ("No incluye")
- Pasarela de pago en línea (fuera de alcance en Sección 5 del PRD).
- Reemplazo o sustitución de medicamentos eliminados dentro de la misma orden (prohibido explícitamente en Sección 3 y 5).
- Generación de notas de crédito o monederos de saldo digital automatizados (la resolución es manual y presencial).
