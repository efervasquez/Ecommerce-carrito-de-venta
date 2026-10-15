# HU-07: Procesamiento de pagos integrado mediante pasarela Stripe en Modo Test

## Historia de usuario
Como Cliente Final  
Quiero pagar mi pedido directamente desde el carrito de compras utilizando una pasarela de pagos integrada  
Para completar mi compra digital de medicamentos de manera rápida, segura y confirmada las 24 horas del día.

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance (3.1 Lo que INCLUYE — Pasarela de Pagos Integrada; 3.2 Lo que NO INCLUYE — Devolución de dinero en efectivo o extornos), 4. Personas y Actores (Cliente Final), 5. Requerimientos Funcionales (RF-06: Pasarela de Pagos Integrada — RF-06.1).
- **Requerimientos Funcionales asociados:** RF-06.1 (*El sistema integrará una pasarela de pagos mediante Stripe operando en Modo Test [Sandbox] para el entorno MVP*).
- **Criterios de éxito y RNF asociados:** RNF-01 (*Tiempo de respuesta <= 2.5s y estabilidad bajo concurrencia*), RNF-02 (*Cifrado SSL/TLS de extremo a extremo, cumplimiento de PCI-DSS y LPDP*), RNF-03 (*Disponibilidad mínima de 99.5% 24/7*), Criterio de éxito — Penetración Digital (*Al menos el 25% de la facturación global proveniente de ventas web según Sección 8 del PRD*), Criterio de éxito — Estabilidad del Sistema (*Disponibilidad mínima del 99.5% 24/7*), AGENTS.md (*Patrón Saga o transacciones MySQL nativas para flujos de pasarela de pagos y liberación de stock; prohibición estricta de almacenar contraseñas o tarjetas de crédito en texto plano o logs*).
- **Cobertura:** Componente seguro de pago embebido (Stripe Elements) en modo pruebas (Test/Sandbox), procesamiento transaccional del cobro con tarjetas de crédito/débito, confirmación de orden de compra, descuento definitivo de stock reservado, asignación del estado inicial `Registrado` en el ciclo de vida del pedido y pantalla de confirmación con número de pedido.

## Criterios de aceptación funcionales
1. **Integración con Stripe en Modo Test (Sandbox):**
   - El sistema integra la API y componentes de cliente de Stripe configurados en ambiente de prueba (Sandbox/Test Mode) para el procesamiento de pagos del MVP.
2. **Seguridad y captura de datos bancarios:**
   - La captura de datos de tarjeta (número, fecha de expiración, CVC) se realiza exclusivamente a través de los componentes seguros de Stripe (Elements).
   - El backend de Botica la Luz nunca almacena ni registra información confidencial de tarjetas de crédito o débito, cumpliendo con las políticas de seguridad de AGENTS.md y RNF-02.
3. **Confirmación de orden y descuento de inventario:**
   - Tras recibir la respuesta satisfactoria de Stripe (`status: succeeded`):
     - El sistema consolida la orden transaccional en la base de datos con un identificador único de pedido.
     - Asigna el estado obligatorio inicial de `Registrado`.
     - Consolida el descuento definitivo de las existencias del inventario previamente reservadas.
     - Limpia los productos del carrito de compras de la sesión del cliente.
     - Despliega una pantalla de confirmación exitosa con el detalle de la compra, monto pagado y número de pedido para seguimiento.
4. **Manejo de transacciones rechazadas o fallidas:**
   - Si la transacción es rechazada por Stripe (fondos insuficientes, tarjeta expirada, bloqueo de emisor o error de tokenización):
     - El sistema no genera la orden de compra ni descuenta definitivamente el inventario.
     - Muestra un mensaje claro al cliente indicando que el pago no pudo procesarse.
     - Mantiene los productos en el carrito de compras para permitir un nuevo intento con otro método de pago.
5. **Inmutabilidad transaccional y política de no reembolsos:**
   - Una vez confirmado el pago, no existen opciones para que el cliente ni el operador soliciten extornos o reembolsos de dinero en la pasarela (política estricta de cero devoluciones monetarias según Sección 3.2 y RF-04.2).

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Procesamiento exitoso de pago con tarjeta en Stripe Test
```gherkin
Feature: Pasarela de pagos Stripe Sandbox
  Scenario: Cliente realiza el pago satisfactorio de su pedido con tarjeta de prueba
    Given que el cliente se encuentra en la pantalla de checkout con productos por un total de "S/ 85.00"
    When ingresa los datos de una tarjeta válida de prueba de Stripe Test y pulsa "Pagar ahora"
    Then Stripe procesa y confirma la transacción de forma exitosa
    And el sistema registra la orden de compra con el estado "Registrado"
    And descuenta definitivamente el stock reservado de los medicamentos
    And vacía los productos del carrito de compras
    And muestra la pantalla de confirmación con el número de pedido "#BL-10045" y el resumen de compra
```

### Escenario 2 — Caso borde: Transacción rechazada por fondos insuficientes en Stripe Test
```gherkin
Feature: Pasarela de pagos Stripe Sandbox
  Scenario: Intento de pago con tarjeta de prueba que simula fondos insuficientes
    Given que el cliente está procesando el pago de su carrito de compras
    When ingresa una tarjeta de prueba de Stripe que emula "fondos insuficientes" y confirma el pago
    Then Stripe retorna un código de rechazo por saldo insuficiente
    And el sistema no crea la orden de pedido ni descuenta el inventario
    And conserva los productos en el carrito de compras
    And muestra una notificación en pantalla indicando "Su pago fue rechazado por saldo insuficiente. Por favor intente con otra tarjeta"
```

## Supuestos
- **Operación en entorno Sandbox:** Se asume que para el MVP todas las transacciones de pago son procesadas exclusivamente con credenciales y tarjetas de prueba de Stripe en Modo Test, sin liquidación ni cargos bancarios reales.

## Puntos Abiertos
- **PA-01 — Reserva de stock:** ¿Cuál es la duración exacta de la sesión/reserva de stock y la regla de liberación automática (inactividad, abandono o timeout)?  
  *(Afecta al tiempo límite disponible que tiene el cliente para completar el formulario de Stripe antes de que el stock reservado expire y sea liberado para otros usuarios).*

## Exclusiones ("No incluye")
- Pagos contra entrega en efectivo o cobros presenciales con terminal POS físico (despacho exclusivo con pago previo confirmado vía Stripe en web).
- Devolución de dinero en efectivo o extornos bancarios: Cláusula cerrada de cero reembolsos por error de cliente o insatisfacción (Sección 3.2 del PRD y RF-04.2).
- Pagos mediante transferencias bancarias manuales con subida de vouchers (no incluido en el MVP).
- Aplicación Móvil Nativa descargable.
