# HU-06: Automatización de recetas médicas mediante OCR y adición directa al carrito

## Historia de usuario
Como Cliente Final  
Quiero adjuntar una fotografía o archivo PDF de mi receta médica mediante la opción "Leer receta"  
Para que el sistema extraiga automáticamente los medicamentos y cantidades, valide las existencias en inventario y me dirija directamente al carrito con los productos cargados, o me alerte si hay quiebre de stock.

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance (3.1 Lo que INCLUYE — Módulo OCR Automatizado para Recetas Médicas), 4. Personas y Actores (Cliente Final), 5. Requerimientos Funcionales (RF-03: Automatización OCR y Carrito de Compras — RF-03.1, RF-03.2).
- **Requerimientos Funcionales asociados:**
  - RF-03.1 (*Al adjuntar una receta médica, el sistema extraerá mediante OCR los componentes/marcas y cantidades prescritas, consultará las existencias locales y, si todo está disponible, insertará los ítems y redirigirá directamente al usuario a la vista del carrito*).
  - RF-03.2 (*Si falta algún medicamento detectado por el OCR en el inventario, el sistema detendrá el proceso y mostrará una alerta explícita indicando la ausencia de stock de dicho producto*).
- **Criterios de éxito y RNF asociados:** RNF-01 (*Rendimiento bajo 250 clientes concurrentes realizando operaciones críticas en paralelo como carga y procesamiento OCR*), RNF-02 (*Cifrado SSL/TLS y cumplimiento estricto con la Ley de Protección de Datos Personales [LPDP] de Perú al procesar recetas médicas*), Criterio de éxito — Eficiencia Operativa (*Disminución del 30% en el volumen de atención manual para consultas y cotizaciones según Sección 8 del PRD*), Supuesto 2 (*El motor OCR mantiene un tiempo de procesamiento base estable para no degradar la experiencia de usuario*).
- **Cobertura:** Componente web con botón explícito "Leer receta", soporte de subida de imágenes (JPG, PNG) y documentos PDF, invocación del servicio OCR para reconocimiento óptico de caracteres médicos, extracción de principios activos / nombres de marcas y dosificación prescrita, validación inmediata contra existencias locales, adición automática de productos al carrito y redirección inmediata en flujo exitoso, o suspensión y emisión de alerta explícita ante quiebre de stock.

## Criterios de aceptación funcionales
1. **Opción explícita de adjunción:** La aplicación web dispone de una opción visible y accesible denominada "Leer receta" que permite al cliente adjuntar una foto o un archivo en formato PDF de su documento médico.
2. **Extracción automatizada (OCR):** El motor OCR procesa el documento adjunto reconociendo los medicamentos prescritos (por marca o principio activo/componente) y la cantidad de unidades indicadas por el profesional de salud.
3. **Cruce inmediato con inventario:** El sistema consulta de manera síncrona el stock local de la botica para todos los medicamentos detectados en la receta.
4. **Flujo automatizado exitoso con redirección:** Si la botica cuenta con stock suficiente de todos y cada uno de los medicamentos identificados en la receta médica:
   - El sistema los inserta de manera automática en el carrito de compras del cliente con las cantidades prescritas.
   - Redirige directamente al cliente a la vista del carrito de compras para que pueda revisar los ítems y continuar inmediatamente hacia el pago.
5. **Descarte de inserción parcial ante stock mixto o insuficiente (PA-03):** Si la botica no cuenta con stock disponible de alguno de los medicamentos extraídos por el OCR — incluyendo el caso de disponibilidad parcial con stock mixto (algunos fármacos con existencias y otros sin ellas):
   - El sistema descarta la inserción parcial automática y suspende el ingreso de la receta completa al carrito, sin cargar los productos que sí tienen existencias.
   - Despliega en pantalla una alerta clara y explícita notificando al cliente cuál o cuáles medicamentos específicos carecen de existencias en el inventario, para que tome una decisión informada.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Carga de receta médica válida con disponibilidad total y redirección automática al carrito
```gherkin
Feature: Automatización OCR de recetas médicas
  Scenario: Cliente adjunta receta con medicamentos disponibles en inventario
    Given que el cliente se encuentra en la plataforma web
    When pulsa en la opción "Leer receta"
    And adjunta un archivo PDF "receta_medica_01.pdf" que prescribe "Amoxicilina 500mg (10 unidades)" y "Paracetamol 500mg (20 unidades)"
    Then el motor OCR procesa el documento e identifica los medicamentos y sus cantidades
    And el sistema verifica que existen más de 10 unidades de "Amoxicilina 500mg" y más de 20 unidades de "Paracetamol 500mg" en stock
    And añade automáticamente ambos productos con sus cantidades al carrito de compras
    And redirige inmediatamente al cliente a la vista del carrito de compras mostrando los productos cargados listos para pagar
```

### Escenario 2 — Caso borde: Receta con medicina agotada que suspende la inserción y muestra alerta de quiebre
```gherkin
Feature: Automatización OCR de recetas médicas
  Scenario: Cliente adjunta receta médica que contiene un medicamento sin existencias
    Given que el cliente pulsa en "Leer receta"
    When adjunta una imagen "receta_foto.jpg" que contiene "Claritromicina 500mg (14 unidades)"
    Then el motor OCR detecta "Claritromicina 500mg" con cantidad "14"
    And el sistema consulta el inventario local y comprueba que el stock actual es "0 unidades"
    Then el sistema suspende la inserción automática en el carrito
    And muestra una alerta explícita en pantalla indicando "Lo sentimos, no contamos con stock disponible de Claritromicina 500mg para completar su receta médica"
    And no redirige al carrito de compras
```

### Escenario 3 — Caso borde: Receta con stock mixto que descarta la inserción parcial
```gherkin
Feature: Automatización OCR de recetas médicas
  Scenario: Receta con algunos medicamentos disponibles y otros agotados descarta la inserción parcial
    Given que el cliente pulsa en "Leer receta"
    When adjunta una receta que prescribe "Amoxicilina 500mg (10 unidades)" y "Claritromicina 500mg (14 unidades)"
    Then el motor OCR detecta ambos medicamentos con sus cantidades
    And el sistema consulta el inventario y comprueba que "Amoxicilina 500mg" cuenta con stock suficiente pero "Claritromicina 500mg" está agotado
    Then el sistema descarta la inserción parcial automática y suspende el ingreso de toda la receta al carrito
    And no carga "Amoxicilina 500mg" en el carrito
    And muestra una alerta explícita indicando que falta stock de "Claritromicina 500mg" para completar la receta
```

## Supuestos
- **Formatos y legibilidad documental:** Se asume que el procesamiento OCR soporta formatos de archivo estándar web (PDF, JPG, PNG) con resolución legible suficiente para identificar principios activos, marcas y cantidades prescritas.

## Puntos Abiertos (Resueltos)
- **PA-03 — OCR con stock mixto:** RESUELTO (31/10/2026). Se **descarta la funcionalidad de inserción parcial**. Ante una receta con stock mixto (algunos medicamentos disponibles y otros no), el sistema suspende la inserción completa de la receta al carrito y alerta explícitamente al cliente los ítems faltantes, para evitar compras incompletas inadvertidas.

## Exclusiones ("No incluye")
- **Consultas Médicas Online / Telemedicina:** No incluye prescripción médica virtual ni consulta diagnóstica interactiva con doctores (Sección 3.2 del PRD).
- Validación de validez de firmas electrónicas médicas o colegiaturas médicas vía servicios externos (fuera de alcance en MVP).
- Aplicación Móvil Nativa.
