# HU-06: Selección de entrega, medio de pago y confirmación del pedido

## Historia de usuario
Como Cliente autenticado con productos en el carrito  
Quiero seleccionar la modalidad de entrega (domicilio o retiro en tienda) y el medio de pago (efectivo o transferencia con comprobante), y confirmar mi pedido  
Para formalizar la orden de compra y remitirla a la farmacia manteniendo la reserva de mis productos  

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance — Incluye (Cliente: Modalidad de entrega, Selección de dirección, Medio de pago, Transferencias y evidencia, Pago en efectivo, Confirmación del pedido), 4. Estados del pedido (`Recibido`), 5. No incluye (*Pasarela de pago en línea*, *Medios de pago distintos de efectivo o transferencia*).
- **Criterios de éxito asociados:** Criterio 1 (*Un cliente registrado puede generar un pedido completo desde la PWA*), Criterio 3 (*Los pedidos permanecen en Recibido, dentro de la bandeja Pedidos recibidos...*).
- **Cobertura:** Selección entre envío a domicilio (usando dirección del perfil o una nueva dirección) o retiro en tienda; selección de medio de pago (efectivo o transferencia bancaria con carga obligatoria de imagen de comprobante en formato JPG, PNG o GIF <= 1 MB); confirmación final del pedido; generación del número de pedido; transición al estado `Recibido` (bandeja `Pedidos recibidos`) con mantenimiento de la reserva de stock.

## Criterios de aceptación funcionales
1. **Modalidad de entrega:**
   - Si elige `Envío a domicilio`: debe poder usar la dirección guardada en su perfil o ingresar una nueva dirección de entrega para este pedido (país, departamento, distrito y calle).
   - Si elige `Retiro en tienda`: no se solicita dirección de despacho.
2. **Medio de pago obligatorio:**
   - Si elige `Transferencia`: es obligatorio adjuntar la imagen de la evidencia/comprobante de la transferencia en formato `JPG`, `PNG` o `GIF`, de peso máximo `1 MB`.
   - Si elige `Efectivo`: se establece la condición de pago al momento de la entrega (pago contra entrega a domicilio o pago al retirar en el mostrador de la tienda).
3. **Confirmación y mantenimiento de reserva:** Al presionar "Confirmar pedido", el sistema valida que las reservas sigan activas, genera el pedido con un identificador único, lo ubica en el estado `Recibido` y lo canaliza a la bandeja `Pedidos recibidos` del farmacéutico.
4. **Persistencia de la reserva:** A partir de la confirmación del pedido, la reserva de stock deja de regirse por el temporizador de 3 minutos del carrito y se mantiene en estado `Recibido` hasta que el pago sea validado o el pedido sea anulado.
5. **Comprobante de pedido:** El cliente visualiza una pantalla de resumen de confirmación con el número de pedido, modalidad de entrega, medio de pago y el estado actual `Recibido`.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Confirmación con entrega a domicilio y pago por transferencia
```gherkin
Feature: Checkout y confirmación de pedido
  Scenario: Cliente confirma pedido a domicilio cargando evidencia de transferencia
    Given que el cliente tiene productos reservados en el carrito
    When selecciona la modalidad "Entrega a domicilio" usando la dirección de su perfil
    And selecciona el medio de pago "Transferencia bancaria"
    And adjunta la imagen "comprobante_banco.png" de 650 KB
    And confirma el pedido
    Then el sistema registra el pedido con estado "Recibido"
    And el pedido ingresa a la bandeja "Pedidos recibidos" del farmacéutico manteniendo la reserva de stock
    And la PWA muestra la pantalla de confirmación con el código de pedido generado
```

### Escenario 2 — Camino feliz: Confirmación con retiro en tienda y pago en efectivo
```gherkin
Feature: Checkout y confirmación de pedido
  Scenario: Cliente confirma pedido para retiro en tienda pagando en efectivo
    Given que el cliente tiene productos reservados en el carrito
    When selecciona la modalidad "Retiro en tienda"
    And selecciona el medio de pago "Efectivo"
    And confirma el pedido
    Then el sistema registra el pedido con estado "Recibido"
    And asigna la condición de cobro de efectivo al momento del retiro
    And el pedido mantiene la reserva de stock en la bandeja "Pedidos recibidos"
```

### Escenario 3 — Caso borde: Intento de confirmar pago por transferencia sin comprobante
```gherkin
Feature: Checkout y confirmación de pedido
  Scenario: Cliente selecciona transferencia pero no adjunta la imagen de evidencia
    Given que el cliente está en el paso de pago del checkout
    When selecciona "Transferencia bancaria" pero no carga ningún archivo
    And presiona "Confirmar pedido"
    Then el sistema impide la confirmación del pedido
    And muestra un mensaje de alerta exigiendo adjuntar la evidencia del pago en formato JPG, PNG o GIF de hasta 1 MB
```

## Puntos Abiertos
- Sin puntos abiertos pendientes. Todas las definiciones fueron confirmadas en el PRD.

## Exclusiones ("No incluye")
- Pasarela de pago en línea con tarjetas de crédito o débito (excluido expresamente en Sección 5 del PRD).
- Medios de pago distintos de efectivo o transferencia (excluido en Sección 5).
- Pagos con billeteras digitales con confirmación automática por API o QR dinámico (solo transferencia tradicional con comprobante estático).
