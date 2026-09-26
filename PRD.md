# PRD — Carrito de compras farmacéutico (PWA)

## 1. Problema

Un cliente no puede realizar compras en línea de productos farmacéuticos y vitaminas. Para generar un pedido debe acercarse a la tienda o realizar una llamada telefónica.

## 2. Actores

- **Cliente:** se registra, consulta el catálogo, arma pedidos, adjunta recetas cuando corresponde, selecciona la modalidad de entrega y pago, y consulta el estado de sus pedidos.
- **Farmacéutico:** valida recetas y pagos, prepara pedidos, gestiona los estados, archiva pedidos pagados no entregados y marca la entrega.
- **Operario:** gestiona el catálogo y el stock de productos.
- **Delivery (externo):** retira y entrega pedidos a domicilio. Informa telefónicamente al farmacéutico cuando el cliente recibe el pedido y realiza el pago. No interactúa con el sistema.

## 3. Alcance — Incluye

### Cliente

- Registro e inicio de sesión obligatorio.
- Datos de registro: documento, nombre, dirección (país, departamento, distrito y calle), teléfono, correo y canal principal de notificación.
- Catálogo de productos farmacéuticos y vitaminas con búsqueda y visualización.
- Identificación clara de los medicamentos que requieren receta.
- Al seleccionar un medicamento que requiere receta, el sistema informa que solo podrá despacharse con receta y solicita adjuntar la imagen antes de agregarlo al pedido.
- Una misma imagen de receta puede respaldar varios medicamentos del mismo pedido.
- Las imágenes de recetas deben estar en formato JPG, PNG o GIF y no superar 1 MB.
- Selección de productos y armado del carrito.
- Reserva de stock al agregar productos al carrito.
- Liberación automática de la reserva si el carrito permanece inactivo durante 3 minutos antes de generar el pedido.
- Liberación de la reserva si el cliente abandona el carrito antes de generar el pedido. Una vez generado, el pedido pasa a la bandeja `Pedidos recibidos` y mantiene la reserva hasta su pago o anulación automática.
- Selección de modalidad de entrega: domicilio o retiro en tienda.
- Selección de dirección: dirección del perfil o una nueva dirección para el pedido.
- Selección obligatoria del medio de pago: efectivo o transferencia.
- Para transferencias, carga de la imagen de evidencia del pago en formato JPG, PNG o GIF, con un tamaño máximo de 1 MB.
- Para efectivo contra entrega o retiro en tienda, pago al momento de recibir o retirar el pedido.
- Confirmación del pedido con validación de disponibilidad y mantenimiento de la reserva hasta la validación del pago.
- Visualización del estado del pedido.
- Anulación de pedidos no pagados desde la PWA cuando todavía no pasaron a `Entregado` o `Archivado`. Si el pedido ya cambió de estado, el cliente debe coordinar la anulación con el farmacéutico.
- Recepción de notificaciones por el canal principal configurado: mensaje de texto, WhatsApp o correo electrónico.

### Farmacéutico

- Visualización de las bandejas operativas del pedido.
- Validación de la receta adjunta y del pago antes de preparar el pedido, excepto cuando el medio de pago es efectivo contra entrega, ya sea a domicilio o con retiro en tienda.
- Aprobación o rechazo de recetas.
- Cuando se rechaza la receta de un medicamento en un pedido con varios productos:
  - Se elimina únicamente ese medicamento.
  - Se libera su stock reservado.
  - Se recalcula el total del pedido.
- Se notifica al cliente el medicamento eliminado y el motivo.
  - El pedido continúa con los demás medicamentos.
- Si el cliente desea otro medicamento, debe generar un nuevo pedido y seguir el flujo completo.
- Si la receta de un medicamento se rechaza en un pedido ya pagado por transferencia, la diferencia de dinero se resuelve manualmente en la farmacia y la notificación informa el medicamento afectado, el motivo del rechazo y ese procedimiento manual.
- Cuando el pedido contiene un único medicamento y su receta es rechazada, el pedido pasa a `Anulado` y se libera el stock reservado.
- Si al preparar o despachar falta stock de un medicamento, se elimina únicamente ese medicamento, se recalcula el total, se libera el stock y se notifica al cliente. Si el pedido ya estaba pagado, la diferencia de dinero se resuelve manualmente en la farmacia, sin reembolso automático. Ese medicamento no puede reemplazarse dentro del mismo pedido; cualquier alternativa requiere un nuevo pedido.
- Si se elimina uno o más medicamentos de un pedido pagado por transferencia, ya sea de forma parcial o por anulación total, cualquier diferencia de dinero se resuelve manualmente en la farmacia, sin reembolso automático.
- Validación de transferencias mediante la evidencia cargada por el cliente.
- Registro del estado de pago `Pagado` después de validar la transferencia o recibir el efectivo.
- Preparación manual del pedido.
- Marcado de la entrega cuando el cliente recibe físicamente el pedido.
- Identificación visual diferenciada en la bandeja `Pedidos recibidos` para los pedidos que contienen medicamentos cuya receta debe validar.
- Para entregas a domicilio con pago contra entrega, recepción de la confirmación telefónica del delivery, validación del pago y cambio del pedido a `Entregado`.
- Anulación automática de pedidos que permanecen en la bandeja `Pedidos recibidos` durante más de 24 horas desde su generación. No aplica a pedidos `En preparación` ni `Pendientes de entrega`. Al anularlos, se libera el stock reservado.
- Anulación manual por parte del cliente o del farmacéutico para pedidos no pagados en cualquier estado anterior a `Entregado` o `Archivado`. Si el pedido ya cambió de estado, el cliente debe coordinar la anulación con el farmacéutico. Los pedidos pagados y no entregados solo pueden pasar a `Archivado`.
- Archivado manual de pedidos pagados y no entregados, con registro obligatorio del motivo y notificación al cliente.
- Conservación indefinida de pedidos archivados.
- Búsqueda de pedidos archivados para entregarlos posteriormente. Cuando el cliente retira el pedido, el farmacéutico lo pasa directamente a `Entregado`.

### Bandejas del farmacéutico

Los pedidos se visualizan en una única bandeja operativa según su estado; no aparecen simultáneamente en varias bandejas:

- **Pedidos recibidos:** incluye todos los pedidos generados por los clientes, incluidos los que contienen medicamentos con receta. La receta debe haber sido adjuntada antes de agregar el medicamento.
- **En preparación:** pedidos cuya receta y pago ya fueron validados y que se están preparando manualmente. Los pedidos con efectivo contra entrega, ya sea a domicilio o con retiro en tienda, se identifican con un color diferenciado, ya que pueden estar pendientes de pago.
- **Pendientes de entrega:** incluye pedidos con transferencia validada y pedidos con efectivo pendiente de cobro, tanto para retiro en tienda como para entrega a domicilio.
- **Entregados:** pedidos recibidos físicamente por el cliente.
- **Archivados:** pedidos pagados y no entregados que el farmacéutico decidió archivar manualmente.
- **Pedidos anulados:** pedidos que fueron anulados automática o manualmente.
- La bandeja `Pedidos anulados` es visible únicamente para el farmacéutico.

`Pagado` es una condición independiente del flujo logístico, aunque el pedido se muestra en una sola bandeja operativa a la vez.

### Operario

- Crear, editar y eliminar productos.
- Categorizar productos y cargar sus fotografías.
- Definir precios.
- Definir si un medicamento requiere receta.
- Ingresar mercadería para actualizar el stock.

### Aplicativo

- Aplicativo PWA (Progressive Web App).
- Roles diferenciados dentro de la misma aplicación: Cliente, Farmacéutico y Operario.
- Notificaciones por un único canal principal configurado por el cliente.
- Historial de pedidos, incluidos los pedidos archivados.
- El cliente puede consultar en su bandeja los pedidos generados y su estado actual, incluidos los pedidos `Anulados` y `Archivados`.

## 4. Estados del pedido

- **Recibido:** pedido generado por el cliente y pendiente de validación de receta y pago. En la interfaz se muestra dentro de la bandeja `Pedidos recibidos`. Los pedidos que requieren validación de receta se identifican visualmente con una marca diferenciada, sin crear un estado adicional.
- **En preparación:** el farmacéutico reúne los medicamentos. La receta debe estar validada; el pago también debe estar validado, salvo cuando el medio de pago es efectivo contra entrega a domicilio o con retiro en tienda.
- **Pendiente de entrega:** pedido preparado y listo para retiro o entrega. Puede tener transferencia validada o efectivo pendiente de cobro.
- **Entregado:** el cliente recibió físicamente el pedido.
- **Anulado:** pedido cancelado automáticamente por superar 24 horas en `Pedidos recibidos`, pedido con un único medicamento cuya receta fue rechazada o pedido no pagado anulado manualmente por el cliente o el farmacéutico antes de `Entregado` o `Archivado`. En este PRD, cancelación manual y anulación manual significan lo mismo. Los pedidos pagados y no entregados no pasan a `Anulado`; pasan a `Archivado`.
- **Archivado:** pedido pagado y no entregado que el farmacéutico archiva manualmente. Conserva el stock y puede pasar posteriormente a `Entregado`.

## 5. Alcance — No incluye (por ahora)

- Pasarela de pago en línea.
- Medio de pago distinto de efectivo o transferencia.
- Módulo de seguimiento del delivery; la coordinación se realiza telefónicamente.
- Envío de notificaciones por múltiples canales simultáneos.
- Ajustes de stock distintos del ingreso de mercadería, como bajas, transferencias entre ubicaciones, caducidad de lotes o inventarios físicos.
- Reemplazo de un medicamento eliminado por falta de stock dentro del mismo pedido.
- Gestión automática de reembolsos o saldos a favor; las diferencias de dinero se resuelven manualmente en la farmacia.
- Autenticación multifactor u otros mecanismos avanzados de seguridad.

## 6. Criterios de éxito

- Un cliente registrado puede generar un pedido completo desde la PWA.
- El sistema impide agregar un medicamento que requiere receta si no se adjunta previamente la imagen correspondiente.
- Los pedidos con medicamentos que requieren receta permanecen en `Recibido`, dentro de la bandeja `Pedidos recibidos`, y muestran una marca visual diferenciada para el farmacéutico.
- Todo pedido con receta adjunta pasa por validación de receta y pago antes de entrar en preparación, salvo el pago en efectivo contra entrega, ya sea a domicilio o con retiro en tienda.
- El sistema reserva stock al agregar productos al carrito y libera inmediatamente la reserva si el carrito se abandona sin confirmar.
- El sistema libera automáticamente la reserva del carrito después de 3 minutos de inactividad antes de generar el pedido.
- El stock se descuenta al validar el pago y se libera cuando un pedido o medicamento se anula.
- El operario puede gestionar productos, precios, fotografías, categorías, requisitos de receta e ingreso de mercadería.
- El farmacéutico puede validar recetas y pagos, preparar pedidos, gestionarlos por bandejas, archivarlos y marcar la entrega.
- Los pedidos a domicilio con pago contra entrega muestran un color diferenciado en la bandeja `En preparación`.
- Un pedido pagado y archivado conserva el stock y puede pasar a `Entregado` cuando el cliente lo retira.
- El cliente recibe notificaciones por los cambios de estado, anulaciones, archivados y eliminación de medicamentos.
- El cliente puede anular pedidos no pagados desde la PWA antes de `Entregado` o `Archivado`; después debe coordinar con el farmacéutico.
- Los pedidos que permanecen en `Pedidos recibidos` durante más de 24 horas desde su generación se anulan automáticamente y liberan el stock reservado. Esta regla no aplica a pedidos `En preparación` ni `Pendientes de entrega`.

## 7. Consideraciones regulatorias y datos sensibles

Se consideran datos sensibles y deben tratarse conforme a la normativa de protección de datos y comercio electrónico aplicable:

- **Datos personales:** documento, nombre, dirección, teléfono, correo y datos necesarios para el pedido.
- **Datos de salud implícitos:** el contenido del pedido y las recetas pueden revelar información de salud.
- **Recetas médicas:** imágenes sensibles; requieren controles de acceso, almacenamiento seguro y validación de Compliance y Seguridad. En la base de datos se conserva la referencia al archivo almacenado en el repositorio.
- **Evidencias de pago:** imágenes de transferencias; deben almacenarse de forma segura.
- **Datos transaccionales:** trazabilidad y auditabilidad de pedidos, pagos, cambios de estado, anulaciones y archivados.

> No se incluye pasarela de pago en esta versión, por lo que no se manejan datos de tarjetas.

## 8. Puntos Abiertos

Sin puntos abiertos de negocio. Todas las definiciones fueron confirmadas con el usuario.

## 9. Próximo paso

Entregar el PRD actualizado al Agente BA para una validación previa de consistencia y completitud.

El Agente BA debe confirmar que no existen inconsistencias ni puntos pendientes de negocio antes de iniciar la redacción de las Historias de Usuario. No debe generar Historias de Usuario hasta emitir dicha confirmación.
