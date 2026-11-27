# HU-11: Reportería y métricas del Backoffice para administradores y supervisores

## Historia de usuario
Como Administrador de Pedidos / Farmacéutico / Operador de Stock (Supervisor)  
Quiero consultar desde un panel de Backoffice reportes consolidados de ventas y facturación, el balance de pedidos por estado y métricas de inventario crítico  
Para tomar decisiones oportunas de reabastecimiento y gestión comercial sin depender de reportes manuales ni de la disponibilidad del ERP.

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance (3.1 Lo que INCLUYE — Módulo de Reportería del Backoffice), 4. Personas y Actores (Administrador de Pedidos / Farmacéutico / Operador de Stock), 5. Requerimientos Funcionales (RF-08: Reportería y Métricas del Backoffice — RF-08.1, RF-08.2, RF-08.3).
- **Requerimientos Funcionales asociados:**
  - RF-08.1 (*El sistema dispondrá de un panel de reportería para el Backoffice que permitirá visualizar reportes consolidados de ventas y facturación en rangos de fechas seleccionables*).
  - RF-08.2 (*El panel presentará el balance de pedidos distribuidos por cada uno de los estados del ciclo de vida [Registrado, Preparando producto, En camino, Entregado]*).
  - RF-08.3 (*El sistema generará reportes de inventario crítico, identificando productos con stock bajo [< 6 unidades], medicamentos con quiebres recurrentes y productos de mayor rotación comercial*).
- **Criterios de éxito y RNF asociados:** RNF-01 (*Rendimiento óptimo bajo concurrencia operativa en Backoffice*), RNF-03 (*Disponibilidad mínima del 99.5% 24/7*), Criterio de éxito — Eficiencia Operativa (*Disminución del 30% en el volumen de atención manual para consultas de stock y cotizaciones según Sección 8 del PRD*), Criterio de éxito — Penetración Digital (*Al menos el 25% de la facturación global proveniente del canal web*), AGENTS.md (*Control de accesos estricto basado en roles RBAC para perfiles administrativos y de supervisión; patrón CQRS para separar lecturas de escrituras en el catálogo*).
- **Cobertura:** Panel de reportería web en el Backoffice con autenticación restringida a roles autorizados, consulta de ventas y facturación por rangos de fechas, balance de pedidos agrupado por los 4 estados del ciclo de vida, y reportes de inventario crítico (stock bajo, quiebres recurrentes y rotación) para reabastecimiento oportuno.

## Criterios de aceptación funcionales
1. **Acceso restringido al panel (RBAC):**
   - Solo usuarios con rol autorizado (Administrador, Supervisor o Farmacéutico) pueden acceder al panel de reportería del Backoffice.
   - Cada acceso y consulta de reportes queda registrado con la identidad del usuario y la marca de tiempo en los logs estructurados del sistema.
2. **Reporte consolidado de ventas y facturación (RF-08.1):**
   - El panel permite seleccionar un rango de fechas (inicio y fin) y visualiza el consolidado de ventas y facturación correspondiente a ese periodo.
   - El reporte muestra al menos: total de órdenes pagadas y confirmadas, unidades vendidas y monto total facturado en el rango seleccionado.
3. **Balance de pedidos por estado (RF-08.2):**
   - El panel presenta la distribución de los pedidos activos distribuidos por cada uno de los 4 estados del ciclo de vida: `Registrado`, `Preparando producto`, `En camino` y `Entregado`.
   - El balance se actualiza conforme cambian de estado las órdenes en el buzón de despacho.
4. **Reporte de inventario crítico (RF-08.3):**
   - El panel genera reportes que identifican:
     - Productos con stock bajo (existencias estrictamente menores a 6 unidades, `stock < 6`).
     - Medicamentos con quiebres de stock recurrentes.
     - Productos de mayor rotación comercial.
   - Estos reportes sirven de insumo para decisiones de reabastecimiento oportuno.
5. **Naturaleza de solo lectura (CQRS):**
   - Las consultas del panel de reportería operan sobre las proyecciones de lectura del catálogo y pedidos, sin alterar las escrituras ni la integridad transaccional del sistema.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Consulta de reporte consolidado de ventas en un rango de fechas
```gherkin
Feature: Reportería y métricas del Backoffice
  Scenario: Supervisor consulta ventas y facturación de un periodo seleccionado
    Given que el supervisor ha iniciado sesión con perfil autorizado en el Backoffice
    When ingresa al panel de reportería y selecciona el rango de fechas "01/10/2026 - 31/10/2026"
    Then el sistema despliega el reporte consolidado del periodo
    And muestra el total de órdenes confirmadas, las unidades vendidas y el monto total facturado
    And registra la consulta en el log de auditoría con la identidad del supervisor y la fecha
```

### Escenario 2 — Caso borde: Reporte de inventario crítico que identifica quiebres recurrentes y stock bajo
```gherkin
Feature: Reportería y métricas del Backoffice
  Scenario: Supervisor consulta inventario crítico con productos bajo mínimos y quiebres recurrentes
    Given que existen productos con existencias menores a 6 unidades y medicamentos con quiebres de stock recurrentes
    When el supervisor solicita el reporte de inventario crítico
    Then el sistema identifica y lista los productos con stock bajo (menos de 6 unidades)
    And marca los medicamentos con quiebres recurrentes de stock
    And ordena los productos de mayor rotación comercial para priorizar el reabastecimiento
```

## Supuestos
- **Consultas de solo lectura:** Se asume que el panel de reportería es estrictamente de lectura y no expone operaciones de modificación sobre ventas, pedidos o inventario.
- **Fuente de datos local:** Se asume que los reportes se construyen sobre los datos transaccionales y de catálogo persistidos en la base de datos MySQL local de la botica, de forma independiente a la disponibilidad del ERP central.

## Puntos Abiertos (Resueltos)
- **PA-05 — Reportería del Backoffice:** RESUELTO (31/10/2026). La Matriz de Reportería del Backoffice se incorpora formalmente al alcance del MVP mediante **RF-08**, dando origen a esta HU.

## Exclusiones ("No incluye")
- Módulo avanzado de Business Intelligence o analítica predictiva (más allá de los reportes operativos descritos en RF-08).
- Reportería financiera o tributaria (SUNAT, declaraciones de impuestos, cuentas corrientes con proveedores).
- Exportación a formatos específicos (PDF, Excel) u orquestación de envíos programados por correo: no especificados en el PRD.
