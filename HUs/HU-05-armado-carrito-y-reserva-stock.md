# HU-05: Armado del carrito y reserva temporal de stock

## Historia de usuario
Como Cliente autenticado  
Quiero agregar productos al carrito de compras, reservar temporalmente su stock y gestionar las cantidades  
Para asegurar la disponibilidad de los productos mientras completo los pasos de compra  

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance — Incluye (Cliente: Carrito, Reserva de stock, Liberación por inactividad de 3 minutos, Abandono de carrito).
- **Criterios de éxito asociados:** Criterio 5 (*El sistema reserva stock al agregar productos al carrito y libera inmediatamente la reserva si el carrito se abandona sin confirmar*) y Criterio 6 (*El sistema libera automáticamente la reserva del carrito después de 3 minutos de inactividad antes de generar el pedido*).
- **Cobertura:** Adición y retiro de ítems del carrito, reserva de stock disponible en tiempo real, temporizador de 3 minutos de inactividad, liberación de stock ante inactividad o abandono de sesión/carrito previo a la generación del pedido.

## Criterios de aceptación funcionales
1. **Reserva de stock inmediata:** Al agregar un producto al carrito (o incrementar su cantidad), el sistema descuenta temporalmente la cantidad del stock disponible general y la asigna a la reserva del carrito del cliente.
2. **Validación de disponibilidad:** Si no hay stock disponible suficiente para la cantidad solicitada, el sistema impide agregar el producto e informa el stock máximo disponible.
3. **Temporizador de inactividad (3 minutos):** Cada interacción del cliente en el carrito o proceso de compra reinicia un temporizador de 3 minutos. Si el usuario permanece inactivo durante más de 3 minutos sin avanzar ni confirmar el pedido:
   - El sistema libera automáticamente todo el stock reservado, regresándolo al stock disponible general.
   - El carrito se desactiva o vacía, notificando en pantalla que la sesión de compra expiró por inactividad.
4. **Liberación por abandono o vaciado:** Si el cliente elimina manualmente un ítem del carrito, el stock de ese ítem se libera inmediatamente. Si el cliente abandona explícitamente el carrito (ej. cerrar sesión o vaciar carrito) antes de generar el pedido, la reserva se libera al instante.
5. **Transición a pedido:** Si el cliente confirma y genera el pedido dentro del tiempo permitido, la reserva de stock se mantiene y el pedido pasa a la bandeja `Pedidos recibidos`.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Adición de producto al carrito y reserva de stock exitosa
```gherkin
Feature: Carrito y reserva de stock
  Scenario: Cliente agrega unidades de un producto con stock disponible
    Given que el producto "Vitamina C 1000mg" tiene un stock disponible de 10 unidades
    When el cliente agrega 2 unidades al carrito de compras
    Then el sistema reserva 2 unidades de "Vitamina C 1000mg" para el cliente
    And el stock disponible general para otros usuarios pasa a ser de 8 unidades
    And inicia el contador de actividad de 3 minutos
```

### Escenario 2 — Caso borde: Liberación automática de stock por inactividad de 3 minutos
```gherkin
Feature: Carrito y reserva de stock
  Scenario: La reserva se libera al cumplirse 3 minutos de inactividad en el carrito
    Given que el cliente tiene 2 unidades de "Vitamina C 1000mg" reservadas en su carrito
    When transcurren 3 minutos sin que el cliente realice ninguna acción ni confirme el pedido
    Then el sistema libera automáticamente las 2 unidades reservadas
    And el stock disponible general del producto se restablece
    And la PWA muestra un aviso indicando que el carrito expiró por inactividad
```

### Escenario 3 — Caso borde: Intento de agregar más unidades de las disponibles en stock
```gherkin
Feature: Carrito y reserva de stock
  Scenario: Cliente intenta agregar una cantidad que excede el stock no reservado
    Given que el producto "Ibuprofeno 400mg" tiene un stock disponible no reservado de 3 unidades
    When el cliente intenta agregar 5 unidades al carrito
    Then el sistema bloquea la adición de 5 unidades
    And muestra un mensaje indicando que solo hay 3 unidades disponibles para reserva
```

## Puntos Abiertos
- Sin puntos abiertos pendientes. Todas las definiciones fueron confirmadas en el PRD.

## Exclusiones ("No incluye")
- Pasarela de pago en línea (fuera de alcance en Sección 5 del PRD).
- Reservas de productos sin agregarlos al carrito (listas de deseos o guardado para después).
- Descuentos de stock permanentes en esta etapa (el stock solo se descuenta formalmente al validar el pago).
