# HU-04: Vista de detalle extendida del producto con información clínica y comercial

## Historia de usuario
Como Cliente Final  
Quiero acceder a la página dedicada de detalle de cualquier producto del catálogo  
Para consultar su información clínica completa (contraindicaciones, advertencias, reacciones adversas, presentación, componentes, requerimiento de receta médica) y métodos de entrega antes de realizar mi compra.

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance (3.1 Lo que INCLUYE — Vista de Detalle del Producto, Reglas de Negocio y Atributos del Producto), 4. Personas y Actores (Cliente Final), 5. Requerimientos Funcionales (RF-02: Catálogo y Experiencia de Usuario — RF-02.3).
- **Requerimientos Funcionales asociados:** RF-02.3 (*Al hacer clic en un ítem, el sistema cargará una página detallada que incluirá: foto, componentes, precio, flag de receta requerida, detalle, presentación, métodos de entrega [delivery/retiro], contraindicaciones, precauciones/advertencias y reacciones adversas*).
- **Criterios de éxito y RNF asociados:** RNF-02 (*Cumplimiento de LPDP y regulaciones sanitarias sobre difusión de información farmacológica*), Criterio de éxito — Eficiencia Operativa (*Disminución del 30% en el volumen de atención manual para consultas de stock y cotizaciones según Sección 8 del PRD*).
- **Cobertura:** Navegación desde la tarjeta de lista hacia la vista de página dedicada del producto, renderizado responsivo de los atributos clínicos, comerciales y logísticos obligatorios, e inclusión de selector de cantidades para agregar al carrito de compras.

## Criterios de aceptación funcionales
1. **Navegación a página dedicada:** Al hacer clic sobre cualquier producto de la lista continua del catálogo, el sistema abre su página dedicada de detalle.
2. **Estructura obligatoria de información:** La vista de detalle debe presentar obligatoriamente los siguientes bloques y datos:
   - **Fotografía del producto:** Imagen principal de alta calidad del empaque o presentación.
   - **Datos comerciales:** Nombre comercial, componentes (principios activos), precio regular y precio con descuento porcentual de oferta (si tiene oferta activa).
   - **Indicador de receta médica:** Flag visual explícito que señale claramente si "Necesita receta para la venta" o si se trata de un "Producto de venta libre".
   - **Detalle y presentación:** Descripción detallada del uso/propósito del producto y su presentación física (tipo de empaque, mililitros [ml], miligramos [mg] o unidades por caja).
   - **Métodos de entrega disponibles:** Indicación expresa de las modalidades admitidas para el producto: "Delivery" (despacho a domicilio) o "Retiro en la misma botica".
   - **Información clínica y advertencias de salud:**
     - Contraindicaciones de uso.
     - Precauciones y advertencias especiales.
     - Reacciones adversas conocidas.
   - **Etiqueta informativa adicional:** Indicador de "Precios bajos" (si aplica al producto).
3. **Acción de compra desde detalle:** La vista debe incluir un control de selección de cantidad numérica y un botón "Agregar al carrito", validando en tiempo real que la cantidad elegida no sobrepase el stock disponible del producto.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Cliente consulta la vista de detalle de un medicamento que requiere receta médica
```gherkin
Feature: Vista de detalle del producto
  Scenario: Cliente visualiza ficha completa de un medicamento bajo receta
    Given que el cliente se encuentra navegando en el catálogo
    When hace clic sobre la tarjeta del producto "Azitromicina 500mg"
    Then el sistema abre la página de detalle dedicada del producto
    And muestra la fotografía, componentes "Azitromicina dihidrato 500mg", precio "S/ 18.50" y presentación "Caja con 3 tabletas recubiertas"
    And exhibe el distintivo visual obligatorio indicando "Necesita receta para la venta"
    And despliega los métodos de entrega habilitados "Delivery y Retiro en botica"
    And muestra las secciones de "Contraindicaciones", "Precauciones/Advertencias" y "Reacciones adversas"
    And permite seleccionar la cantidad y pulsar "Agregar al carrito"
```

### Escenario 2 — Caso borde: Visualización de producto de venta libre sin contraindicaciones restrictivas
```gherkin
Feature: Vista de detalle del producto
  Scenario: Cliente consulta producto de venta libre con etiqueta de precios bajos
    Given que el cliente hace clic en el producto "Vitamina C 1000mg efervescente"
    When carga la página de detalle dedicada
    Then el sistema muestra la indicación "Producto de venta libre"
    And muestra la etiqueta informativa "Precios bajos"
    And presenta las precauciones de consumo generales y los métodos de entrega disponibles
    And permite añadir el producto directamente al carrito de compras
```

## Supuestos
- **Acción de compra en vista de detalle (extensión operativa):** Aunque RF-02.3 enumera prioritariamente los campos informativos y clínicos obligatorios de la ficha, se asume como extensión operativa estándar de e-commerce la inclusión del selector de cantidad y el botón "Agregar al carrito" en esta vista para permitir la conversión directa del cliente sin obligarlo a retornar a la lista de búsqueda.

## Puntos Abiertos
- **PA-02 — Etiqueta "Precios bajos":** ¿Qué criterio activa la etiqueta "Precios bajos" en un producto?  
  *(Aplica a la visualización de la etiqueta comercial en la vista de detalle; sin asumir si es manual desde Backoffice o derivada de una regla automática).*

## Exclusiones ("No incluye")
- **Consultas Médicas Online / Telemedicina:** No incluye chats médicos en vivo, consultas de diagnóstico médico online ni recomendaciones farmacológicas automatizadas por IA (Sección 3.2 del PRD).
- Calificación o valoraciones con comentarios de clientes no estipulados en el PRD.
- Aplicación Móvil Nativa descargable de tiendas (operación exclusiva como Web App Responsive).
