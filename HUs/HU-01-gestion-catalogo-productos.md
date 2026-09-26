# HU-01: Gestión del catálogo de productos farmacéuticos y vitaminas

## Historia de usuario
Como Operario de farmacia  
Quiero crear, editar, categorizar y dar de baja productos en el catálogo  
Para mantener actualizada la oferta comercial, precios, imágenes e indicar los medicamentos que requieren receta médica  

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance — Incluye (Operario), 2. Actores (Operario).
- **Criterios de éxito asociados:** Criterio 7 (*El operario puede gestionar productos, precios, fotografías, categorías, requisitos de receta e ingreso de mercadería*).
- **Cobertura:** Creación de nuevos productos, edición de datos comerciales, asignación de fotografías, categorización (medicamentos, vitaminas, etc.), asignación de precios y configuración obligatoria del indicador booleano de si el medicamento requiere receta médica.

## Criterios de aceptación funcionales
1. **Atributos obligatorios:** Todo producto debe contener nombre, descripción, categoría, precio de venta, fotografía del producto y la indicación booleana de si "Requiere receta médica" (Sí/No).
2. **Definición de precios:** El precio debe ser un valor numérico positivo en moneda nacional.
3. **Fotografías de producto:** Se debe permitir la carga y actualización de imágenes del producto (formatos estándar web).
4. **Flag de receta médica:** El operario puede marcar o desmarcar si el producto exige receta médica para su despacho. Si está marcado, el sistema activará los controles de adjunción de receta para el cliente.
5. **Eliminación o baja de productos:** El operario puede eliminar o desactivar productos del catálogo para que no aparezcan disponibles para la venta.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Creación exitosa de un medicamento que requiere receta
```gherkin
Feature: Gestión de catálogo de productos
  Scenario: Operario registra satisfactoriamente un medicamento con requerimiento de receta
    Given que el operario ha iniciado sesión en el módulo de gestión del aplicativo
    When ingresa el nombre "Amoxicilina 500mg", selecciona la categoría "Antibióticos", asigna el precio "15.50", carga la fotografía del empaque y activa la opción "Requiere receta médica"
    And guarda el producto
    Then el producto queda registrado en el catálogo
    And queda disponible para visualización con la identificación de requerimiento de receta activa
```

### Escenario 2 — Caso borde: Intento de guardar un producto con precio inválido
```gherkin
Feature: Gestión de catálogo de productos
  Scenario: Operario intenta registrar un producto con precio negativo o cero
    Given que el operario se encuentra en el formulario de creación de productos
    When completa los campos obligatorios pero ingresa un precio de "-5.00"
    And intenta guardar el producto
    Then el sistema impide el guardado
    And muestra un mensaje de validación indicando que el precio debe ser un valor numérico positivo mayor a cero
```

## Puntos Abiertos
- Sin puntos abiertos pendientes. Todas las definiciones fueron confirmadas en el PRD.

## Exclusiones ("No incluye")
- Pasarela de pago en línea (fuera de alcance en Sección 5 del PRD).
- Carga masiva automatizada de productos mediante archivos CSV/Excel (no contemplado en el PRD).
- Gestión de listas de precios diferenciadas por cliente o promociones automáticas.
- Ajustes de inventario desde la pantalla de edición de producto (el stock se gestiona exclusivamente por ingreso de mercadería).
