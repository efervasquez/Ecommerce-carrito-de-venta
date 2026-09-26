# HU-15: Archivado manual de pedidos pagados y entrega posterior

## Historia de usuario
Como Farmacéutico  
Quiero archivar manualmente los pedidos pagados que no hayan podido ser entregados (registrando el motivo obligatorio) y poder buscarlos después para pasarlos directamente a Entregado  
Para resguardar los pedidos pagados pendientes de recojo indefinidamente sin liberar su stock y formalizar la entrega cuando el cliente se presente  

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance — Incluye (Farmacéutico: Archivado manual de pedidos pagados y no entregados, Registro de motivo obligatorio, Notificación al cliente, Conservación indefinida de stock, Búsqueda y pase directo a `Entregado`), 3. Bandejas (`Archivados`), 4. Estados (`Archivado`), 6. Criterios de éxito (Criterio 10).
- **Criterios de éxito asociados:** Criterio 10 (*Un pedido pagado y archivado conserva el stock y puede pasar a Entregado cuando el cliente lo retira*), Criterio 8 (*El farmacéutico puede... archivarlos y marcar la entrega*), Criterio 11 (*El cliente recibe notificaciones por... archivados...*).
- **Cobertura:** Acción de archivado en bandeja para pedidos con condición `Pagado` y no entregados; captura obligatoria del motivo del archivado; notificación al cliente con el motivo; mantenimiento indefinido de las unidades físicas y stock descontado; visualización en la bandeja `Archivados`; buscador de pedidos archivados; acción de reactivación/entrega que transiciona el pedido archivado directamente a `Entregado`.

## Criterios de aceptación funcionales
1. **Condición estricta de archivado:** Solo se puede archivar un pedido si está en condición `Pagado` y aún no ha sido entregado físicamente (estados previos como `En preparación` o `Pendiente de entrega`).
2. **Registro obligatorio del motivo:** Al presionar "Archivar pedido", el sistema exige ingresar de forma obligatoria un texto descriptivo con el motivo del archivo (ej. "Cliente no atendió al repartidor", "Cliente solicitó guardar su pedido para fin de mes"). Sin este texto no se permite archivar.
3. **Notificación al cliente:** Al completarse el archivado, el sistema notifica al cliente por su canal principal informándole que su pedido pagado ha sido archivado en custodia de la farmacia, indicando el motivo registrado.
4. **Conservación indefinida de stock:** Los productos de un pedido archivado no liberan stock ni retornan al catálogo disponible; las unidades permanecen descontadas y custodiadas en la farmacia de manera indefinida.
5. **Búsqueda en bandeja de Archivados:** La bandeja `Archivados` permite buscar por código de pedido, documento del cliente o nombre para ubicar rápidamente la orden cuando el cliente se apersone a la farmacia.
6. **Entrega posterior directa:** Cuando el cliente acude finalmente a retirar su pedido archivado, el farmacéutico presiona la acción "Entregar pedido archivado", lo cual transiciona el pedido directamente al estado `Entregado` y lo mueve a la bandeja `Entregados` sin pasar nuevamente por preparación.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Archivado de un pedido pagado no entregado
```gherkin
Feature: Archivado manual y entrega posterior
  Scenario: Farmacéutico archiva un pedido pagado que el cliente no fue a recoger
    Given que el pedido "PED-1101" se encuentra en "Pendientes de entrega" con condición "Pagado" y retiro en tienda
    When el farmacéutico selecciona "Archivar pedido"
    And escribe en el campo de motivo obligatorio: "Cliente no retiró en la fecha límite; se custodiará en almacén"
    And confirma la operación
    Then el pedido cambia al estado "Archivado" y se traslada a la bandeja "Archivados"
    And el stock de los productos se conserva descontado indefinidamente
    And se envía una notificación al cliente indicándole que su pedido está archivado con el motivo registrado
```

### Escenario 2 — Camino feliz: Entrega física de un pedido previamente archivado
```gherkin
Feature: Archivado manual y entrega posterior
  Scenario: Cliente acude semanas después a recoger un pedido archivado
    Given que el pedido "PED-1102" está en la bandeja "Archivados"
    When el cliente se presenta en la farmacia y el farmacéutico busca "PED-1102" en la bandeja
    And presiona "Marcar como entregado"
    Then el sistema cambia el estado del pedido "PED-1102" directamente a "Entregado"
    And lo traslada a la bandeja "Entregados"
    And envía la notificación de entrega final al cliente
```

### Escenario 3 — Caso borde: Intento de archivar sin registrar el motivo
```gherkin
Feature: Archivado manual y entrega posterior
  Scenario: Farmacéutico intenta archivar un pedido pagado dejando el motivo vacío
    Given que el pedido "PED-1103" es apto para archivar
    When el farmacéutico presiona "Archivar pedido" pero deja el campo motivo en blanco
    And presiona confirmar
    Then el sistema impide el archivado
    And muestra un mensaje de validación indicando que el registro del motivo es estrictamente obligatorio
```

## Puntos Abiertos
- Sin puntos abiertos pendientes. Todas las definiciones fueron confirmadas en el PRD.

## Exclusiones ("No incluye")
- Pasarela de pago en línea (fuera de alcance en Sección 5 del PRD).
- Destrucción, reingreso a stock o cobro de penalidades por custodia de pedidos archivados (el PRD estipula conservación indefinida).
- Paso de un pedido archivado a estado `Anulado` (los pedidos pagados nunca pasan a Anulado).
