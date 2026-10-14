# HU-05: Carrito de compras con persistencia ligada a sesión y visualización prioritaria de ofertas

## Historia de usuario
Como Cliente Final  
Quiero que mi carrito de compras conserve los productos seleccionados durante mi sesión activa y despliegue prioritariamente en la parte superior aquellos productos que tengan ofertas activas  
Para no perder mi selección mientras navego y aprovechar de forma clara las promociones vigentes antes de proceder al pago.

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance (3.1 Lo que INCLUYE — Carrito de Compras con Persistencia e Interfaz Orientada a Ofertas), 4. Personas y Actores (Cliente Final), 5. Requerimientos Funcionales (RF-03: Automatización OCR y Carrito de Compras — RF-03.3).
- **Requerimientos Funcionales asociados:** RF-03.3 (*El sistema ordenará la interfaz del carrito de compras colocando todos los productos que tengan ofertas activas en la sección superior inicial de la pantalla. Selección y reserva de productos ligada estrictamente a la duración de la sesión del cliente*).
- **Criterios de éxito y RNF asociados:** RNF-01 (*Tiempo de respuesta <= 2.5s en procesamiento de carritos bajo carga sostenida de 250 clientes concurrentes*), AGENTS.md (*Optimización de recursos y pool de conexiones en MySQL; tareas programadas de ciclo de vida para carritos*).
- **Cobertura:** Almacenamiento y persistencia del estado del carrito ligado al token/sesión del cliente, ordenamiento obligatorio de la interfaz con bloque superior prioritario para productos con ofertas, sección secundaria para productos regulares, actualización interactiva de cantidades, cálculo de totales y reserva temporal de inventario.

## Criterios de aceptación funcionales
1. **Persistencia del carrito ligada a la sesión:**
   - Todo producto agregado se almacena en el carrito vinculado a la sesión activa del cliente.
   - Si el usuario refresca el navegador, cambia de página en el catálogo o ingresa a la vista de detalle de un producto, el contenido de su carrito se mantiene intacto.
2. **Sección prioritaria de ofertas en el carrito:**
   - Al abrir la vista del carrito de compras, la pantalla debe desplegar de forma obligatoria y en la parte superior inicial una sección destacada con todos los productos que posean ofertas y descuentos porcentuales activos.
   - En este bloque se muestra claramente el precio original tachado, el porcentaje de descuento y el precio final con descuento.
3. **Sección de productos a precio regular:**
   - Debajo del bloque prioritario de ofertas, el carrito lista los productos convencionales que no tienen descuento activo.
4. **Modificación de cantidades y recálculo interactivo:**
   - El cliente puede incrementar o reducir las unidades de cualquier producto en el carrito, o eliminarlo mediante un botón de supresión.
   - El sistema valida que las unidades solicitadas no excedan el stock disponible.
   - La interfaz recalcula en tiempo real los subtotales por producto, el total de ahorro por descuentos y el importe final a pagar.
5. **Reserva temporal de stock:**
   - Cada producto en el carrito genera un bloqueo/reserva temporal de inventario asociado a la sesión activa del cliente para garantizar la disponibilidad durante el armado del pedido.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Visualización prioritaria de productos en oferta en el encabezado del carrito
```gherkin
Feature: Carrito de compras con persistencia y ofertas
  Scenario: Cliente abre el carrito que contiene productos regulares y productos con oferta
    Given que el cliente tiene en su carrito 1 "Paracetamol 500mg" (precio regular S/ 5.00)
    And 1 "Protector Solar SPF 50+" con oferta activa del 20% de descuento (precio original S/ 50.00, con descuento S/ 40.00)
    When el cliente ingresa a la vista del carrito de compras
    Then el sistema renderiza en la parte superior inicial la sección prioritaria de "Productos en Oferta"
    And exhibe en dicha sección el "Protector Solar SPF 50+" indicando "20% DSCTO" y precio de "S/ 40.00"
    And renderiza en la parte inferior los demás productos regulares incluyendo "Paracetamol 500mg"
    And muestra el total consolidado a pagar por "S/ 45.00" y un ahorro de "S/ 10.00"
```

### Escenario 2 — Caso borde: Modificación de cantidad superando el stock disponible del producto
```gherkin
Feature: Carrito de compras con persistencia y ofertas
  Scenario: Cliente intenta incrementar la cantidad de un producto más allá de las existencias reales
    Given que el producto "Jarabe Antitusígeno 120ml" tiene un stock disponible de 4 unidades
    And el cliente tiene actualmente 4 unidades de dicho jarabe en su carrito de compras
    When el cliente pulsa el botón "+" para solicitar una 5ta unidad
    Then el sistema bloquea el incremento
    And mantiene la cantidad en 4 unidades
    And muestra un mensaje de advertencia indicando "Stock máximo disponible alcanzado (4 unidades)"
```

## Puntos Abiertos
- **PA-01 — Reserva de stock:** ¿Cuál es la duración exacta de la sesión/reserva de stock y la regla de liberación automática (inactividad, abandono o timeout)?  
  *(Pregunta exacta a negocio: Se requiere definir el lapso en minutos de validez de la reserva y si la liberación del stock ocurre por inactividad de sesión, cierre explícito de navegador o timeout transaccional en el carrito).*

## Exclusiones ("No incluye")
- Cupones de descuento promocionales manuales o códigos alfanuméricos ingresados por el usuario (no contemplado en el PRD).
- Devolución de dinero en efectivo o extornos tras concretar el pago (política estricta de no reembolso de la Sección 3.2).
- Aplicación Móvil Nativa descargable.
