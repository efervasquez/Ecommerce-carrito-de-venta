# HU-04: Consulta de catálogo y adjunción obligatoria de receta médica

## Historia de usuario
Como Cliente autenticado  
Quiero explorar el catálogo de productos farmacéuticos y vitaminas, identificar qué medicamentos exigen receta y adjuntar la imagen correspondiente  
Para poder agregar medicamentos regulados a mi pedido cumpliendo la normativa  

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance — Incluye (Cliente: Catálogo, Identificación de medicamentos con receta, Adjunción obligatoria, Reutilización de receta, Formatos y tamaño), 7. Consideraciones regulatorias y datos sensibles.
- **Criterios de éxito asociados:** Criterio 2 (*El sistema impide agregar un medicamento que requiere receta si no se adjunta previamente la imagen correspondiente*).
- **Cobertura:** Visualización y búsqueda de productos, distintivo visual de "Requiere receta médica", bloqueo de agregado sin receta, modal/formulario de carga de receta en formatos JPG, PNG o GIF (máximo 1 MB), opción de asociar una receta previamente cargada en la misma sesión/pedido a otros medicamentos con receta.

## Criterios de aceptación funcionales
1. **Búsqueda y visualización:** El catálogo debe permitir filtrar por categoría (medicamentos, vitaminas) y buscar productos por nombre.
2. **Distintivo de receta obligatoria:** Todo producto marcado por el operario como "Requiere receta" debe mostrar una etiqueta visual clara e inequívoca en su ficha y en la vista de catálogo.
3. **Bloqueo preventivo:** Si el cliente hace clic en agregar un medicamento que requiere receta y no hay una receta adjunta, el sistema debe desplegar un aviso informativo indicando que solo podrá despacharse con receta médica e impedir agregar el producto hasta adjuntarla.
4. **Formatos y tamaño de archivo:** La imagen de la receta médica debe ser en formato `JPG`, `PNG` o `GIF`, y su tamaño no debe superar `1 MB`. Archivos de otros formatos (ej. PDF) o superiores a 1 MB deben ser rechazados con mensaje explicativo.
5. **Reutilización de receta en el mismo pedido:** Si el cliente ya adjuntó una receta para un medicamento dentro del pedido actual, el sistema debe permitirle asociar esa misma receta para respaldar otros medicamentos que agregue posteriormente sin obligarlo a subir el archivo nuevamente.
6. **Almacenamiento seguro:** La imagen se almacena en el repositorio seguro y se conserva su referencia en base de datos bajo las consideraciones de datos sensibles.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Cliente adjunta receta válida y agrega medicamento al pedido
```gherkin
Feature: Consulta de catálogo y adjunción de receta
  Scenario: Cliente adjunta una imagen de receta médica válida y agrega el medicamento
    Given que el cliente está autenticado y visualiza el producto "Amoxicilina 500mg" que requiere receta médica
    When hace clic en "Agregar al pedido"
    Then el sistema muestra el mensaje informativo "Este medicamento requiere receta médica para su despacho" y solicita adjuntar la imagen
    When el cliente carga el archivo "receta_amoxicilina.jpg" de 800 KB en formato JPG
    And confirma la adjunción
    Then el sistema acepta el archivo
    And permite agregar "Amoxicilina 500mg" al carrito de compras
```

### Escenario 2 — Camino feliz: Reutilización de receta previamente cargada en el mismo pedido
```gherkin
Feature: Consulta de catálogo y adjunción de receta
  Scenario: Cliente reutiliza una receta médica ya cargada para un segundo medicamento regulado
    Given que el cliente ya cargó la receta "receta_general.png" para el producto "Azitromicina" en su pedido actual
    When selecciona el producto "Ibuprofeno 800mg" que también requiere receta médica
    Then el sistema le ofrece la opción de "Usar receta ya adjunta (receta_general.png)" o "Subir nueva receta"
    When el cliente selecciona "Usar receta ya adjunta"
    Then el producto "Ibuprofeno 800mg" queda respaldado por dicha imagen y se agrega al pedido
```

### Escenario 3 — Caso borde: Intento de cargar un archivo con formato o peso no permitido
```gherkin
Feature: Consulta de catálogo y adjunción de receta
  Scenario: Cliente intenta subir un archivo PDF o una imagen superior a 1 MB
    Given que el cliente intenta agregar un medicamento que requiere receta médica
    When intenta cargar un archivo "receta.pdf" o una imagen "foto_receta.png" de 2.5 MB
    Then el sistema rechaza la carga
    And muestra un mensaje de error indicando que solo se admiten imágenes en formato JPG, PNG o GIF de hasta 1 MB
    And el medicamento no se agrega al carrito
```

## Puntos Abiertos
- Sin puntos abiertos pendientes. Todas las definiciones fueron confirmadas en el PRD.

## Exclusiones ("No incluye")
- Pasarela de pago en línea (fuera de alcance en Sección 5 del PRD).
- Reconocimiento óptico de caracteres (OCR) o validación automatizada por IA del texto de la receta médica (la validación es humana y la realiza el farmacéutico).
- Validación de fecha de caducidad médica o firma digital de la receta en el momento de la carga.
