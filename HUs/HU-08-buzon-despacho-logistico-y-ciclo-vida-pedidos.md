# HU-08: Buzón de despacho logístico, consolidación geográfica de rutas y control de ciclo de vida

## Historia de usuario
Como Administrador de Pedidos / Supervisor logístico  
Quiero centralizar las órdenes confirmadas en un buzón de despacho, consolidar rutas por cercanía geográfica, asignarlas a motorizados y controlar su ciclo de vida en 4 estados obligatorios  
Para optimizar los tiempos de entrega de medicamentos, ordenar las salidas de los repartidores y mantener el seguimiento fidedigno de cada orden.

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance (3.1 Lo que INCLUYE — Buzón de Despacho Logístico [Gestión de Pedidos]), 4. Personas y Actores (Administrador de Pedidos, Motorizado), 5. Requerimientos Funcionales (RF-07: Buzón de Despacho Logístico — RF-07.1, RF-07.2, RF-07.3).
- **Requerimientos Funcionales asociados:**
  - RF-07.1 (*El sistema centralizará las órdenes confirmadas y consolidará las rutas de despacho por cercanía geográfica de zona*).
  - RF-07.2 (*El sistema asignará los pedidos a motorizados por orden de llegada o mediante auto-asignación manual*).
  - RF-07.3 (*El ciclo de vida del pedido estará controlado por 4 estados obligatorios: Registrado, Preparando producto, En camino y Entregado*).
- **Criterios de éxito y RNF asociados:** RNF-01 (*Rendimiento óptimo bajo concurrencia operativa en Backoffice*), Criterio de éxito 1 (*Disminución del 30% en carga operativa manual y agilización de entregas*), AGENTS.md (*Arquitectura orientada a eventos EDA y trazabilidad estructurada de cambios de estado*).
- **Cobertura:** Bandeja centralizada de pedidos en el Backoffice, agrupación y filtrado por cercanía geográfica / zonas de reparto, asignación de pedidos a motorizados propios (por orden de llegada o auto-asignación), y control estricto de la máquina de estados con las 4 transiciones obligatorias.

## Criterios de aceptación funcionales
1. **Centralización en el buzón logístico:** Toda orden pagada y confirmada en la tienda ingresa inmediatamente al buzón de despacho con el estado obligatorio inicial de `Registrado`.
2. **Consolidación de rutas por cercanía geográfica:**
   - La interfaz del buzón agrupa las órdenes confirmadas según su distrito, zona o cercanía geográfica de destino.
   - Permite al supervisor visualizar paquetes de pedidos cercanos para organizar salidas consolidadas y minimizar tiempos de traslado.
3. **Mecanismos de asignación a motorizados:**
   - **Asignación por supervisor:** El administrador de pedidos puede seleccionar un lote de órdenes de una misma zona y asignarlas a un motorizado específico de la botica.
   - **Auto-asignación por orden de llegada:** Los motorizados pueden acceder a la lista de pedidos pendientes en su zona y auto-asignarse las órdenes según orden de llegada cronológico.
4. **Ciclo de vida controlado por 4 estados obligatorios:**
   - El sistema valida y controla que el pedido transicione únicamente por los siguientes 4 estados:
     1. `Registrado`: Orden confirmada y pagada, a la espera de preparación.
     2. `Preparando producto`: El equipo de botica selecciona y empaqueta físicamente los medicamentos e insumos.
     3. `En camino`: El motorizado retira el paquete empaquetado e inicia la ruta hacia la dirección del cliente.
     4. `Entregado`: El motorizado culmina la entrega física al cliente en su domicilio.
5. **Restricción de transiciones arbitrarias:**
   - El sistema impide saltos de estado incongruentes (por ejemplo, no se puede marcar `Entregado` una orden que está en `Registrado` sin haber pasado por `Preparando producto` y `En camino`).
   - Cada cambio de estado almacena fecha, hora exacta y el identificador del usuario responsable (auditoría y trazabilidad).

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Consolidación por zona, asignación y progresión secuencial de los 4 estados
```gherkin
Feature: Buzón de despacho logístico y ciclo de vida de pedidos
  Scenario: Supervisor agrupa pedidos por cercanía y motorizado completa la entrega secuencial
    Given que existen 3 pedidos confirmados en estado "Registrado" para la zona "San Isidro"
    When el supervisor ingresa al buzón de despacho y agrupa las 3 órdenes por cercanía geográfica
    And asigna la ruta al motorizado "Carlos Ruiz"
    Then los pedidos cambian al estado "Preparando producto"
    When el personal de botica termina el empaque y el motorizado inicia la ruta
    Then los pedidos avanzan al estado "En camino"
    When el motorizado arriba al domicilio y entrega el pedido al cliente
    And confirma la entrega en el sistema
    Then el pedido transiciona al estado final "Entregado"
```

### Escenario 2 — Caso borde: Intento de saltar transiciones obligatorias en el ciclo de vida del pedido
```gherkin
Feature: Buzón de despacho logístico y ciclo de vida de pedidos
  Scenario: Operador intenta marcar directamente como "Entregado" un pedido recién registrado
    Given que un pedido con ID "#BL-2001" se encuentra en estado "Registrado"
    When un operador intenta forzar el cambio de estado directamente a "Entregado"
    Then el sistema bloquea la operación
    And emite un error de validación indicando "Transición de estado inválida: el pedido debe pasar primero por 'Preparando producto' y 'En camino'"
    And mantiene el pedido en estado "Registrado"
```

## Puntos Abiertos
- **PA-04 — Reclamos en el ciclo de vida:** ¿El flujo de reclamos por mal estado debe reflejarse con uno o más estados adicionales en el ciclo de vida del pedido (por ejemplo: *En reclamo*, *Reemplazo en camino*), o se gestiona como un sub-flujo independiente posterior al estado `Entregado`?  
  *(Pregunta exacta a negocio: Se requiere confirmar si los 4 estados descritos en RF-07.3 son los únicos del pedido principal o si la incidencia de reclamo añade estados transaccionales al ciclo de vida global).*

## Exclusiones ("No incluye")
- Seguimiento telemático con GPS en tiempo real de la motocicleta sobre mapa satelital interactivo en la vista del cliente.
- Tercerización logística con empresas de mensajería externas (couriers comerciales); la logística opera exclusivamente con repartidores propios de Botica la Luz.
- Aplicación Móvil Nativa para motorizados (operación mediante Web App Responsive optimizada para navegador móvil).
