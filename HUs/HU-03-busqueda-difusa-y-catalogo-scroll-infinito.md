# HU-03: Catálogo digital en scroll infinito y buscador difuso (Fuzzy Search) con tarjeta de producto

## Historia de usuario
Como Cliente Final  
Quiero buscar medicamentos e insumos mediante un buscador difuso tolerante a errores ortográficos y explorar el catálogo en una lista continua de scroll infinito  
Para encontrar rápidamente productos con su información esencial (foto, componentes, precio regular, ofertas, stock bajo o etiqueta de precios bajos) y agregarlos directamente al carrito de compras.

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance (3.1 Lo que INCLUYE — Catálogo Digital y Buscador Avanzado [Fuzzy Search], Reglas de Negocio y Atributos del Producto), 4. Personas y Actores (Cliente Final), 5. Requerimientos Funcionales (RF-02: Catálogo y Experiencia de Usuario — RF-02.1, RF-02.2).
- **Requerimientos Funcionales asociados:**
  - RF-02.1 (*El motor de búsqueda implementará Fuzzy Search y renderizará los resultados de arriba a abajo en una sola lista sin paginación — scroll infinito*).
  - RF-02.2 (*La tarjeta del producto en la lista presentará de forma obligatoria: foto, nombre, componentes, precio, porcentaje de descuento por oferta [si aplica], alerta de stock bajo [< 6 unidades] o etiqueta de "Precios bajos", y el botón "Agregar al carrito"*).
- **Criterios de éxito y RNF asociados:** RNF-01 (*Concurrencia de hasta 250 clientes y tiempo de respuesta <= 2.5s para búsquedas en el catálogo*), Criterio de éxito — Eficiencia Operativa (*Disminución del 30% en el volumen de atención manual para consultas de stock y cotizaciones según Sección 8 del PRD*).
- **Cobertura:** Motor de búsqueda con tolerancia a errores de tipeo en nombres y principios activos, renderizado continuo vertical con carga dinámica (scroll infinito sin botones de paginación), tarjeta de producto estandarizada con todos sus campos obligatorios y botón de adición directa al carrito.

## Criterios de aceptación funcionales
1. **Búsqueda difusa (*Fuzzy Search*):**
   - El buscador procesa cadenas de texto ingresadas por el cliente tolerando errores ortográficos, omisiones de letras o fallas comunes de digitación (ejemplo: mapear *"camiaa"* a *"camisa"*, *"paracetaml"* a *"paracetamol"*).
   - Realiza la búsqueda tanto sobre el nombre comercial del producto como sobre sus componentes (principios activos).
2. **Visualización en scroll infinito:**
   - Los productos se presentan en una lista continua de arriba hacia abajo.
   - A medida que el usuario se desplaza verticalmente, el sistema carga de manera fluida y asíncrona nuevos productos sin recargar la página web y sin mostrar barras de paginación numérica ("1, 2, 3...").
3. **Campos obligatorios en la tarjeta de producto (Lista):** Cada ítem desplegado en la lista debe contener visiblemente:
   - Fotografía del producto.
   - Nombre comercial del producto.
   - Componentes principales (principios activos).
   - Precio regular en moneda local.
   - Porcentaje de descuento por oferta (únicamente si el producto cuenta con una promoción u oferta activa).
   - Indicador visual especial: alerta de stock bajo cuando las existencias disponibles sean estrictamente menores a 6 unidades (`stock < 6`), O la etiqueta distintiva de "Precios bajos" (asignada manualmente por el operador/farmacéutico en la ficha del producto desde el catálogo/Backoffice — PA-02).
   - Botón directo y accesible: "Agregar al carrito".
4. **Adición directa al carrito de compras:** Al hacer clic en el botón "Agregar al carrito" de la tarjeta, el producto se añade de inmediato a la sesión activa del carrito del cliente, actualizando el contador global sin interrumpir la navegación ni sacar al cliente del catálogo.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Búsqueda difusa de medicamento con error de tipeo y agregación al carrito desde la tarjeta
```gherkin
Feature: Búsqueda y catálogo en scroll infinito
  Scenario: Cliente busca un medicamento con error ortográfico y lo agrega al carrito
    Given que el cliente se encuentra en la página principal del catálogo
    When escribe "ibuprofno 400" en la barra de búsqueda
    Then el motor de búsqueda difusa identifica la coincidencia con "Ibuprofeno 400mg"
    And renderiza en la lista la tarjeta del producto mostrando foto, nombre "Ibuprofeno 400mg", componentes "Ibuprofeno", precio regular "S/ 12.00" y botón "Agregar al carrito"
    When el cliente hace clic en "Agregar al carrito" de dicha tarjeta
    Then el sistema añade 1 unidad de "Ibuprofeno 400mg" al carrito de compras de la sesión
    And actualiza el contador de artículos del carrito a "1" manteniéndose en la misma lista
```

### Escenario 2 — Caso borde: Visualización de alerta de stock bajo en tarjeta con menos de 6 unidades
```gherkin
Feature: Búsqueda y catálogo en scroll infinito
  Scenario: Despliegue de tarjeta de producto con existencia menor a 6 unidades
    Given que el producto "Amoxicilina + Ácido Clavulánico 500/125mg" tiene únicamente 3 unidades disponibles en inventario
    When el cliente busca o navega en el catálogo continuo hasta visualizar dicho producto
    Then la tarjeta del producto despliega obligatoriamente una alerta visual destacada indicando "Últimas unidades disponibles (menos de 6 en stock)"
    And muestra el botón "Agregar al carrito" habilitado para la compra de las existencias restantes
```

## Supuestos
- **Alcance del motor difuso:** Se asume que el algoritmo de búsqueda difusa (*Fuzzy Search*) indexa y compara tanto el nombre comercial del medicamento como sus componentes (principios activos), asegurando la localización del producto aún ante errores de tipeo.
- **Activación manual de la etiqueta "Precios bajos" (PA-02):** Confirmado por el Product Owner el 31/10/2026 — la etiqueta es de asignación manual por el operador o farmacéutico directamente en la ficha del producto; no responde a umbrales automáticos de precio ni a comparadores de mercado.

## Puntos Abiertos (Resueltos)
- **PA-02 — Etiqueta "Precios bajos":** RESUELTO (31/10/2026). La etiqueta es de asignación **manual** por el operador o farmacéutico, activada o desactivada directamente en la ficha del producto desde el catálogo/Backoffice.

## Exclusiones ("No incluye")
- Paginación tradicional con controles de número de página ("Página 1, 2, 3") o botones "Siguiente / Anterior" (excluido explícitamente en el Alcance 3.1).
- Aplicación Móvil Nativa (Android/iOS descargable de tiendas).
- Filtros avanzados de laboratorio farmacéutico o forma galénica no especificados en el PRD.
