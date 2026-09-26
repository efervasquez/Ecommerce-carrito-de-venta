# HU-07: Visualización de estado, historial de pedidos y notificaciones del cliente

## Historia de usuario
Como Cliente autenticado  
Quiero consultar en la PWA el estado actual y el historial de todos mis pedidos, y recibir alertas en mi canal configurado  
Para conocer el avance de mis compras (preparación, entrega, anulación o archivo) y estar informado ante cualquier eventualidad  

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance — Incluye (Cliente: Visualización del estado, Notificaciones por canal principal), 3. Aplicativo (Historial de pedidos, Consulta de estados incluidos Anulados y Archivados), 5. No incluye (*Módulo de seguimiento del delivery*, *Notificaciones por múltiples canales simultáneos*).
- **Criterios de éxito asociados:** Criterio 11 (*El cliente recibe notificaciones por los cambios de estado, anulaciones, archivados y eliminación de medicamentos*).
- **Cobertura:** Pantalla de historial de pedidos en la PWA con filtro/listado de pedidos en curso y pasados (incluyendo estados `Recibido`, `En preparación`, `Pendiente de entrega`, `Entregado`, `Anulado` y `Archivado`). Envío de notificaciones automáticas ante cada cambio de estado o evento relevante a través exclusivamente del canal principal configurado (SMS, WhatsApp o Correo electrónico).

## Criterios de aceptación funcionales
1. **Acceso al historial:** El cliente debe tener una sección "Mis Pedidos" en la PWA donde visualiza todos sus pedidos ordenados cronológicamente.
2. **Visibilidad completa de estados:** Cada pedido debe mostrar su código, fecha, monto total recalculado, modalidad de entrega y estado actual: `Recibido`, `En preparación`, `Pendiente de entrega`, `Entregado`, `Anulado` o `Archivado`.
3. **Disparador de notificaciones:** El sistema debe emitir una notificación automática al cliente cada vez que ocurra uno de los siguientes eventos:
   - Pedido confirmado en `Recibido`.
   - Pedido pasa a `En preparación`.
   - Medicamento eliminado por receta rechazada o falta de stock (con indicación del producto y motivo).
   - Pedido pasa a `Pendiente de entrega`.
   - Pedido pasa a `Entregado`.
   - Pedido pasa a `Anulado` (automática o manualmente).
   - Pedido pasa a `Archivado` (con indicación del motivo registrado por la farmacia).
4. **Canal exclusivo:** La notificación debe enviarse única y estrictamente por el canal principal que el cliente tiene configurado en su perfil (mensaje de texto, WhatsApp o correo electrónico); nunca por más de un canal de forma simultánea.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Cliente consulta estado y recibe notificación por WhatsApp
```gherkin
Feature: Historial y notificaciones de cliente
  Scenario: Cliente con canal WhatsApp recibe notificación cuando su pedido entra en preparación
    Given que el cliente tiene configurado "WhatsApp" como su canal principal de notificación
    And su pedido "PED-101" pasa del estado "Recibido" al estado "En preparación"
    When el sistema registra el cambio de estado
    Then se envía un mensaje de WhatsApp al número del cliente informándole que su pedido "PED-101" está siendo preparado
    And cuando el cliente ingresa a "Mis Pedidos" en la PWA, visualiza el estado "En preparación"
```

### Escenario 2 — Camino feliz: Consulta de pedido archivado en el historial del cliente
```gherkin
Feature: Historial y notificaciones de cliente
  Scenario: Cliente visualiza un pedido archivado con su motivo en la PWA
    Given que el pedido "PED-202" pagado por el cliente fue archivado por la farmacia con el motivo "Cliente no acudió a recoger en fecha acordada"
    When el cliente accede a su historial de pedidos en la PWA
    Then el pedido "PED-202" se muestra listado con el estado "Archivado"
    And al hacer clic en el detalle, puede visualizar el motivo registrado por el farmacéutico
```

### Escenario 3 — Caso borde: Notificación ante eliminación parcial de medicamento
```gherkin
Feature: Historial y notificaciones de cliente
  Scenario: Cliente con canal Correo electrónico recibe notificación de eliminación de un medicamento
    Given que el cliente tiene configurado "Correo electrónico" como canal principal
    When el farmacéutico elimina el producto "Antibiótico X" del pedido "PED-303" por receta rechazada
    Then el sistema envía un correo al cliente detallando el medicamento eliminado, el motivo del rechazo y el nuevo total del pedido
```

## Puntos Abiertos
- Sin puntos abiertos pendientes. Todas las definiciones fueron confirmadas en el PRD.

## Exclusiones ("No incluye")
- Pasarela de pago en línea (fuera de alcance en Sección 5 del PRD).
- Módulo de rastreo o geolocalización en mapa en tiempo real del repartidor (delivery externo se coordina telefónicamente según Sección 2 y 5).
- Envío simultáneo a múltiples canales (ej. enviar a la vez SMS y WhatsApp).
