# HU-09: Gestión de reclamos por producto en mal estado, logística inversa en campo y política de cero reembolsos

## Historia de usuario
Como Cliente Final y Motorizado  
Quiero registrar un reclamo por medicamento en mal estado adjuntando comprobante y fotografía, para que se despache un producto de reemplazo y el motorizado verifique físicamente el cambio en campo hasta un máximo de 3 intentos  
Para resolver incidencias de calidad de forma segura y transparente, respetando la política estricta de no reembolsos monetarios.

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance (3.1 Lo que INCLUYE — Flujo de Reclamaciones por Mal Estado e Inmodificabilidad Transaccional; 3.2 Lo que NO INCLUYE — Devolución de dinero en efectivo o extornos), 4. Personas y Actores (Cliente Final, Motorizado), 5. Requerimientos Funcionales (RF-04: Logística Inversa y Gestión de Reclamos — RF-04.1, RF-04.2, RF-04.3).
- **Requerimientos Funcionales asociados:**
  - RF-04.1 (*El sistema permitirá registrar reclamos por mal estado obligando a adjuntar la foto del producto dañado y el comprobante. Esto disparará la orden de despacho de un motorizado con un producto de reemplazo*).
  - RF-04.2 (*El sistema bloqueará cualquier opción de reembolso o devolución de dinero, tanto en la interfaz del cliente como en la del administrador*).
  - RF-04.3 (*El sistema permitirá registrar hasta un máximo de 3 intentos adicionales secuenciales de cambio en campo administrados por la hoja de ruta del motorizado antes de marcar la incidencia como escalada o cerrada*).
  - RF-04.4 (*El flujo de reclamos opera como un sub-flujo posterior manual e independiente una vez que la orden alcanza el estado Entregado, sin crear estados adicionales en el ciclo de vida del pedido*).
- **Criterios de éxito y RNF asociados:** RNF-02 (*Cumplimiento de LPDP y protección de evidencias adjuntas*), Criterio de éxito — Eficiencia Operativa (*Disminución del 30% en el volumen de atención manual y resolución estructurada de incidencias según Sección 8 del PRD*), AGENTS.md (*Inmutabilidad de eventos y trazabilidad en logística inversa*).
- **Cobertura:** Formulario de registro de reclamo para el cliente con adjunción obligatoria de foto del producto dañado y comprobante de pago, generación de orden de reposición para motorizado propio, verificación física presencial en domicilio (comprobante original, pertenencia a Botica la Luz y evidencia de deterioro), control de hoja de ruta con hasta 3 intentos adicionales de cambio físico ante fallas sucesivas, y bloqueo total de opciones de devolución de dinero en todos los perfiles de usuario.

## Criterios de aceptación funcionales
1. **Registro obligatorio del reclamo con evidencias:**
   - El cliente dispone de un formulario de reclamo exclusivo para productos en mal estado.
   - Es condición obligatoria para enviar la solicitud adjuntar:
     1. Fotografía nítida del medicamento/empaque dañado.
     2. Fotografía o archivo digital del comprobante de pago original emitido por la botica.
   - Sin ambos recaudos, el sistema impide el registro del reclamo.
2. **Disparo de reposición y despacho:**
   - Al registrarse y validarse preliminarmente el reclamo, el sistema genera de forma automática una orden de reposición para preparar un nuevo medicamento idéntico en botica y asignarlo a la hoja de ruta de un motorizado propio.
3. **Validación física en campo por el motorizado:**
   - Al llegar al domicilio, el motorizado actúa como enlace técnico de validación presencial y debe verificar estrictamente:
     1. Que el cliente presente físicamente el comprobante de pago original.
     2. Que el producto a devolver pertenezca fehacientemente a "Botica la Luz" (lote/etiqueta).
     3. Que el producto se encuentre efectivamente en mal estado o presente los defectos reportados.
   - Solo tras corroborar favorablemente estos 3 puntos, el motorizado entrega el nuevo producto y recoge el artículo dañado.
4. **Límite de 3 intentos adicionales de cambio en campo:**
   - Si durante la inspección presencial el nuevo producto de reemplazo presentado por el motorizado también exhibe fallas o mal estado:
     - El motorizado registra la incidencia en su hoja de ruta digital.
     - El sistema permite programar hasta un número máximo de 3 intentos adicionales secuenciales de cambio en campo.
     - Si se agota el 3er intento adicional sin lograr una entrega conforme, el sistema bloquea nuevos despachos automáticos y marca el reclamo como "Escalado a supervisión" para resolución gerencial.
5. **Política estricta de Cero Reembolsos (No Reembolso):**
   - El sistema bloquea a nivel de código y base de datos cualquier opción de reembolso, extorno o devolución de dinero en efectivo o digital, tanto en la interfaz del cliente como en el panel de control del administrador.
    - Si el cliente argumenta equivocación o arrepentimiento en su compra, el sistema no admite el trámite de reclamo ni de cambio.
6. **Sub-flujo posterior manual tras la entrega (PA-04):**
   - El flujo de reclamos por mal estado opera como un sub-flujo posterior, manual e independiente, y solo puede iniciarse una vez que la orden ha alcanzado el estado `Entregado`.
   - No altera los 4 estados base del pedido (`Registrado`, `Preparando producto`, `En camino`, `Entregado`) ni crea estados adicionales en su ciclo de vida; el reclamo gestiona su propia entidad de logística inversa vinculada a la orden original.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Registro de reclamo por mal estado, reposición y validación física exitosa en campo
```gherkin
Feature: Gestión de reclamos y logística inversa en campo
  Scenario: Cliente reporta medicina dañada y motorizado valida presencialmente el cambio
    Given que el cliente recibió su pedido con un frasco quebrado
    When completa el formulario de reclamo adjuntando la fotografía del frasco quebrado y el comprobante de pago original
    And envía la solicitud de reclamo
    Then el sistema registra el reclamo y genera una orden de reemplazo para despacho con motorizado propio
    When el motorizado acude al domicilio del cliente con el producto nuevo
    And verifica físicamente el comprobante original del cliente, la pertenencia a Botica la Luz y el frasco quebrado
    And confirma la conformidad física en su hoja de ruta digital
    Then el motorizado hace entrega del nuevo producto y retira el dañado
    And el sistema registra el reclamo como resuelto satisfactoriamente por cambio físico
```

### Escenario 2 — Caso borde: Persistencia de falla alcanzando el límite máximo de 3 intentos adicionales de cambio
```gherkin
Feature: Gestión de reclamos y logística inversa en campo
  Scenario: Reposición reiterada en campo alcanza el límite de 3 intentos adicionales
    Given que un reclamo ya tuvo su primera entrega con falla y se encuentra en su 3er intento adicional de cambio
    When el motorizado inspecciona el producto en campo junto al cliente y este vuelve a presentar defecto de empaque
    And el motorizado registra el fallo del 3er intento adicional en el sistema
    Then el sistema verifica que se ha alcanzado el límite estricto de 3 intentos adicionales permitidos
    And bloquea la programación de un 4to despacho de cambio
    And actualiza el estado de la incidencia a "Escalado a supervisión" para auditoría administrativa
    And no habilita bajo ningún concepto la devolución de dinero ni extorno
```

## Supuestos
- **Identidad del producto de reemplazo:** Se asume que el producto de reemplazo preparado en botica corresponde al mismo medicamento y presentación del comprobante original.
- **Validación síncrona en campo:** Se asume que la comprobación física de comprobante y pertenencia a la botica es efectuada presencialmente por el motorizado de manera sincrónica al momento de la entrega en domicilio.

## Puntos Abiertos (Resueltos)
- **PA-04 — Reclamos en el ciclo de vida:** RESUELTO (31/10/2026). Los reclamos por mal estado se gestionan como un **sub-flujo posterior manual e independiente** tras la recepción del pedido en estado `Entregado`. El reclamo no impacta directamente el estado de la orden original ni crea estados adicionales; se apertura una entidad independiente de logística inversa vinculada a la orden.

## Exclusiones ("No incluye")
- **Devolución de dinero en efectivo o extornos:** Cláusula cerrada de cero reembolsos por error de cliente o insatisfacción (Sección 3.2 del PRD y RF-04.2).
- Cambios de producto solicitados por error, confusión de dosis o arrepentimiento del comprador (solo procede ante producto dañado o en mal estado).
- Aplicación Móvil Nativa.
