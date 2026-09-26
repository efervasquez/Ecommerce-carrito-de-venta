# HU-10: Validación de transferencias bancarias y registro de pago

## Historia de usuario
Como Farmacéutico  
Quiero revisar la imagen de evidencia de transferencia bancaria adjunta a un pedido y registrar la condición de Pagado  
Para constatar el ingreso del dinero en la cuenta de la farmacia y habilitar el pase del pedido a preparación  

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance — Incluye (Farmacéutico: Validación de transferencias, Registro del estado de pago `Pagado`), 3. Bandejas del farmacéutico (`Pagado` como condición independiente), 7. Evidencias de pago (datos sensibles).
- **Criterios de éxito asociados:** Criterio 4 (*Todo pedido con receta adjunta pasa por validación de receta y pago antes de entrar en preparación...*), Criterio 6 (*El stock se descuenta al validar el pago...*), Criterio 8 (*El farmacéutico puede validar recetas y pagos...*).
- **Cobertura:** Visualización y apertura del archivo de imagen de comprobante bancario (JPG, PNG o GIF); verificación visual contra movimientos bancarios; acción de marcar la condición `Pagado`; descuento formal del stock reservado; habilitación de la transición hacia la bandeja `En preparación`.

## Criterios de aceptación funcionales
1. **Acceso al comprobante:** Para todo pedido con medio de pago `Transferencia`, el farmacéutico puede ver y ampliar la imagen del comprobante de pago subida por el cliente.
2. **Acción de registro de pago:** Si la transferencia es conforme con el monto total del pedido, el farmacéutico presiona la acción para registrar el pago, marcando la condición del pedido como `Pagado`.
3. **Descuento formal de inventario:** Al registrar la condición de `Pagado`, las unidades previamente en calidad de "reserva de stock" se descuentan formal y definitivamente del inventario del sistema.
4. **Habilitación de preparación:**
   - Si el pedido no requiere receta médica: el registro del pago habilita inmediatamente el pase a `En preparación`.
   - Si el pedido requiere receta médica: se requiere que tanto la receta esté aprobada como el pago esté validado para que el pedido pueda avanzar a `En preparación`.
5. **Comprobante observado o no conforme:** Si la imagen es ilegible, no coincide con el monto o no se verifica en cuenta, el farmacéutico no registra el pago y el pedido permanece en `Pedidos recibidos` sujeto a la regla de vencimiento de 24 horas o coordinación de anulación.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Validación exitosa de transferencia bancaria
```gherkin
Feature: Validación de transferencias
  Scenario: Farmacéutico valida evidencia de transferencia bancaria y registra el pago
    Given que el pedido "PED-601" con medio de pago "Transferencia" está en la bandeja "Pedidos recibidos" con total de S/ 85.00
    When el farmacéutico visualiza la imagen del comprobante "voucher_banco.jpg", corrobora los datos bancarios y presiona "Validar y registrar pago"
    Then el sistema registra la condición del pedido como "Pagado"
    And descuenta definitivamente del inventario el stock que estaba reservado
    And el pedido queda habilitado para pasar a la bandeja "En preparación"
```

### Escenario 2 — Caso borde: Transferencia no validada mantiene el pedido en Pedidos recibidos
```gherkin
Feature: Validación de transferencias
  Scenario: Farmacéutico revisa un comprobante ilegible o no acreditado en cuenta
    Given que el pedido "PED-602" tiene un comprobante de transferencia borroso
    When el farmacéutico revisa la evidencia y no puede constatar el abono
    Then no marca la condición de "Pagado"
    And el pedido se mantiene en la bandeja "Pedidos recibidos" sin descontar stock definitivo ni autorizar el inicio de preparación
```

## Puntos Abiertos
- Sin puntos abiertos pendientes. Todas las definiciones fueron confirmadas en el PRD.

## Exclusiones ("No incluye")
- Pasarela de pago en línea (fuera de alcance en Sección 5 del PRD).
- Integración por API directa con entidades bancarias para conciliación automática en tiempo real (la validación es visual y manual por el farmacéutico).
- Cobro con tarjetas mediante terminales POS virtuales o pasarelas de pago (excluido en Sección 5).
