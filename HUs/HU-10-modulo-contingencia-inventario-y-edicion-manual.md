# HU-10: Módulo de contingencia para registro, edición integral de productos y ajuste manual de stock

## Historia de usuario
Como Operador de Stock / Farmacéutico / Administrador  
Quiero contar con un panel manual independiente en el Backoffice para dar de alta nuevos productos, actualizar existencias y modificar integralmente sus atributos comerciales y clínicos  
Para mantener operativo el catálogo y resguardar la exactitud del stock ante interrupciones de conectividad o caídas de las APIs del ERP central.

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance (3.1 Lo que INCLUYE — Módulo de Contingencia y Gestión Manual de Stock, Reglas de Negocio y Atributos del Producto), 4. Personas y Actores (Administrador de Pedidos / Farmacéutico / Operador de Stock), 5. Requerimientos Funcionales (RF-05: Módulo de Stock Manual [Contingencia] — RF-05.1, RF-05.2).
- **Requerimientos Funcionales asociados:**
  - RF-05.1 (*El Backoffice dispondrá de un módulo de inventario manual e independiente que permitirá dar de alta nuevos productos y actualizar la cantidad de stock de forma directa*).
  - RF-05.2 (*El módulo manual permitirá la edición total de la estructura de datos del producto descrita en este PRD [precios, ofertas, descripciones clínicas, requisitos de receta] para mitigar pérdidas de conexión con las APIs del ERP principal*).
- **Criterios de éxito y RNF asociados:** RNF-03 (*Operación continua y disponibilidad mínima de 99.5% 24/7 mitigando caídas externas*), AGENTS.md (*Control de accesos estricto basado en roles RBAC para perfiles administrativos y de farmacia*).
- **Cobertura:** Módulo web en Backoffice con autenticación restringida para operadores autorizados, formulario para registro de nuevos medicamentos e insumos, actualización manual e inmediata del stock numérico, y edición exhaustiva de los campos comerciales y sanitarios de cualquier producto.

## Criterios de aceptación funcionales
1. **Operación autónoma e independiente:** El módulo opera desacoplado de las APIs del ERP central, permitiendo realizar consultas, altas y actualizaciones directamente sobre la base de datos local de la botica sin depender de la conectividad externa.
2. **Alta manual de nuevos productos:**
   - El operador puede registrar nuevos productos en el catálogo completando los campos obligatorios:
     - Nombre comercial.
     - Componentes (principios activos).
     - Precio regular.
     - Fotografía del producto.
     - Stock disponible inicial.
     - Presentación (tipo de empaque, miligramos, mililitros o unidades).
     - Métodos de entrega disponibles: selección de "Delivery", "Retiro en botica" o ambos.
     - Flag lógico de prescripción: "Necesita receta para la venta" (o producto de venta libre).
     - Información clínica: descripción detallada, contraindicaciones, precauciones/advertencias y reacciones adversas.
3. **Ajuste manual directo de stock:**
   - La interfaz permite buscar productos existentes por nombre o componente y modificar de forma inmediata su número de unidades en existencia (stock disponible).
   - Los cambios de existencias se reflejan en tiempo real para las búsquedas y reservas del carrito de compras.
4. **Edición integral de la estructura de datos del producto:**
   - El operador tiene la facultad de modificar la totalidad de los datos del producto descritos en el PRD:
     - Precios regulares.
     - Marca de oferta activa y asignación del porcentaje de descuento correspondiente.
     - Asignación de la etiqueta de "Precios bajos".
     - Actualización o reemplazo de la fotografía del producto.
     - Modificación del flag de requisito de receta médica.
     - Textos clínicos y sanitarios (contraindicaciones, advertencias, reacciones adversas).
5. **Seguridad y auditoría interna:**
   - Solo usuarios con rol autorizado (Administrador, Farmacéutico u Operador de Stock bajo RBAC) pueden acceder a este módulo.
   - Cada alta, cambio de stock o modificación de atributos registra la identidad del usuario y la marca de tiempo de la acción en los logs estructurados del sistema.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Operador actualiza manualmente existencias y activa oferta con descuento en contingencia
```gherkin
Feature: Módulo de contingencia de inventario y edición manual
  Scenario: Farmacéutico actualiza existencias e introduce oferta durante caída del ERP
    Given que la conexión con el ERP central se encuentra interrumpida
    And el farmacéutico ha iniciado sesión con perfil autorizado en el Backoffice
    When busca el producto "Omeprazol 20mg" en el módulo manual de inventario
    And incrementa las existencias a "50 unidades"
    And activa la marca de oferta asignando un "15% de descuento"
    And pulsa el botón "Guardar cambios"
    Then el sistema actualiza inmediatamente los datos en la base de datos local
    And el catálogo digital refleja el nuevo stock de 50 unidades y la etiqueta de oferta del 15%
    And genera un registro de auditoría con el usuario y la hora de la modificación
```

### Escenario 2 — Caso borde: Intento de registro de producto con stock numérico negativo o incompleto
```gherkin
Feature: Módulo de contingencia de inventario y edición manual
  Scenario: Operador intenta registrar una actualización de stock con valor negativo
    Given que el operador se encuentra editando el inventario de un producto
    When ingresa "-10" en el campo de existencias de stock
    And pulsa "Guardar"
    Then el sistema bloquea la actualización
    And resalta el campo de stock con un mensaje indicando "La cantidad de existencias debe ser un número entero mayor o igual a cero"
    And no altera el inventario actual en la base de datos
```

## Puntos Abiertos
- **PA-02 — Etiqueta "Precios bajos":** ¿Qué criterio activa la etiqueta "Precios bajos" en un producto?  
  *(Aplica a la interfaz de edición: si se muestra como un selector manual booleano que el operador activa/desactiva a discreción, o si debe obedecer a una regla del sistema).*
- **PA-05 — Reportería del Backoffice:** El changelog v1.1 menciona la "matriz de reportería del Backoffice" que no figura en el Alcance. ¿Se incorpora al alcance (y se define su RF) o se elimina la mención del changelog?  
  *(Pregunta exacta a negocio: Se requiere definir si el Backoffice debe contemplar pantallas formales de reportes de rotación/stock o si queda formalmente fuera del alcance del MVP).*

## Exclusiones ("No incluye")
- Sincronización automática bidireccional en tiempo real con el ERP central (este módulo es exclusivamente el mecanismo de contingencia manual ante caídas de la integración).
- Módulos de facturación electrónica compleja (SUNAT/declaraciones tributarias) o cuentas corrientes con proveedores (fuera del alcance MVP).
- Módulo avanzado de Business Intelligence o reportería financiera (sujeto a la resolución del Punto Abierto PA-05).
