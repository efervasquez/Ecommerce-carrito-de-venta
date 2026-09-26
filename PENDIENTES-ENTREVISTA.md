# Preguntas pendientes identificadas por el BA

**Proyecto:** Carrito de compras farmacéutico (PWA)  
**Objetivo:** Resolver las definiciones pendientes antes de aprobar el PRD y comenzar las Historias de Usuario.

---

## 1. Reserva de stock en el carrito

1. Antes de generar el pedido, si el cliente deja el carrito abierto sin abandonarlo explícitamente, ¿existe un tiempo máximo de inactividad para liberar automáticamente la reserva de stock?
Si 3 minutos.

## 2. Anulación manual

2. ¿Se confirma que el cliente no puede cancelar pedidos desde la PWA y que la anulación manual es una facultad exclusiva del farmacéutico?
El cliente puede anular los pedidos que ve generados, si cambio de estado podria anularlos coordinando con el farmacéutico.
3. ¿La anulación manual puede realizarse únicamente sobre pedidos no pagados y en estados anteriores a `Entregado` o `Archivado`?
SI
## 3. Receta rechazada en pedido pagado

4. Si se rechaza una receta en un pedido ya pagado por transferencia, ¿la diferencia de dinero se resuelve manualmente en la farmacia tanto si se elimina un medicamento como si se anula todo el pedido?
SI
5. En ese caso, ¿la notificación al cliente debe informar el medicamento afectado, el motivo del rechazo y que la diferencia se resolverá manualmente en la farmacia?
SI

## 4. Recetas adjuntas

6. ¿El cliente debe adjuntar una receta independiente por cada medicamento que la requiere, o una misma imagen puede respaldar varios medicamentos del pedido?
Si puede ser la misma imagen.

## 5. Archivos adjuntos

7. ¿Qué formatos de archivo se permiten para las recetas médicas y los comprobantes de transferencia?
JPG, PNG, GIF.
8. ¿Cuál es el tamaño máximo permitido para cada archivo adjunto?
1 MB.

## 6. Pedidos anulados

9. ¿La bandeja `Pedidos anulados` será visible para el farmacéutico y el operario, o únicamente para el farmacéutico?
solo para el farmacéutico
10. ¿El cliente podrá consultar los pedidos anulados desde su historial?
si en su bandeja el podra ver los pedidos que genero y su estado actual. Incluso si el pedido paso a anulado o archivado.
---

## Nota para el equipo

No se incorporan valores predeterminados para tiempos, permisos, formatos ni tamaños de archivos. Estas decisiones deben ser confirmadas por el usuario antes de aprobar el PRD y comenzar las Historias de Usuario.
