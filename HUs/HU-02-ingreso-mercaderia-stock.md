# HU-02: Ingreso de mercadería para actualización de stock

## Historia de usuario
Como Operario de farmacia  
Quiero registrar el ingreso de mercadería de productos existentes  
Para incrementar el stock disponible para la venta en el catálogo  

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance — Incluye (Operario), 5. Alcance — No incluye (*Ajustes de stock distintos del ingreso de mercadería*).
- **Criterios de éxito asociados:** Criterio 7 (*El operario puede gestionar [...] e ingreso de mercadería*).
- **Cobertura:** Selección de un producto existente en el catálogo, ingreso de la cantidad de unidades recibidas y actualización inmediata del stock disponible total.

## Criterios de aceptación funcionales
1. **Selección de producto:** El operario debe poder buscar y seleccionar cualquier producto activo registrado en el catálogo.
2. **Cantidad positiva:** La cantidad ingresada debe ser un número entero positivo mayor a cero.
3. **Actualización de stock:** Al confirmar el ingreso, el sistema suma la cantidad ingresada al stock físico disponible actual del producto.
4. **Registro transaccional:** Cada ingreso de mercadería debe registrar fecha, hora, operario responsable, producto y cantidad ingresada para fines de auditabilidad.
5. **Restricción de operaciones:** El operario únicamente puede sumar stock mediante esta funcionalidad; no se permiten registros de disminución o ajustes negativos.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Ingreso regular de mercadería a un producto
```gherkin
Feature: Ingreso de mercadería
  Scenario: Operario incrementa el stock de un medicamento
    Given que el producto "Paracetamol 500mg" cuenta con un stock disponible de 20 unidades
    When el operario selecciona el producto e ingresa una cantidad de 50 unidades de mercadería recibida
    And confirma la operación
    Then el sistema actualiza el stock disponible del producto a 70 unidades
    And registra la transacción con la fecha, hora y datos del operario
```

### Escenario 2 — Caso borde: Intento de ingresar cantidad no válida
```gherkin
Feature: Ingreso de mercadería
  Scenario: Operario intenta registrar un ingreso de 0 o cantidad negativa
    Given que el operario está en la interfaz de ingreso de mercadería
    When selecciona un producto e intenta registrar una cantidad de 0 o "-10" unidades
    Then el sistema bloquea la confirmación
    And muestra un mensaje de error indicando que la cantidad a ingresar debe ser un número entero mayor a cero
```

## Puntos Abiertos
- Sin puntos abiertos pendientes. Todas las definiciones fueron confirmadas en el PRD.

## Exclusiones ("No incluye")
- Pasarela de pago en línea (fuera de alcance en Sección 5 del PRD).
- Ajustes de stock por mermas, caducidad de lotes o roturas (excluido explícitamente en Sección 5).
- Transferencias de stock entre almacenes o sedes (excluido en Sección 5).
- Tomas de inventario físico o conciliación de inventario (excluido en Sección 5).
