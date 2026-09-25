# PRD — Carrito de compras farmacéutico (PWA)

## 1. Problema

Un cliente no puede realizar compras en línea de productos farmacéuticos y vitaminas. Para generar un pedido debe acercarse a la tienda o realizar una llamada telefónica.

## 2. Actores

- **Cliente:** realiza pedidos en línea.
- **Farmacéutico:** vende el producto / atiende el pedido.
- **Operario:** gestiona el stock (ingreso de mercadería).

## 3. Alcance — Incluye

- Generar un pedido en el carrito de compras.
- Seleccionar productos del catálogo.
- Validar stock disponible.
- Ingreso de mercadería.
- Aplicativo PWA (Progressive Web App).
- Algunos medicamentos solicitan receta.

## 4. Alcance — No incluye (por ahora)

- Pasarela de pago.

## 5. Funcionalidades

- Catálogo de productos (farmacéuticos y vitaminas).
- Selección de productos y armado del carrito.
- Generación de pedido.
- Validación de stock disponible antes de confirmar el pedido.
- Ingreso de mercadería (operario) que alimenta el stock.
- Aplicativo PWA.
- Solicitud de receta para ciertos medicamentos.

## 6. Consideraciones regulatorias / datos sensibles

Se marcan como **datos sensibles** los siguientes, y deberán tratarse conforme a la normativa de protección de datos y comercio electrónico aplicable:

- **Datos personales del cliente:** nombre, dirección, teléfono y datos de contacto necesarios para el pedido.
- **Datos de salud implícitos:** el contenido del pedido (medicamentos, vitaminas y recetas) revela información de salud del cliente y debe tratarse con mayor protección.
- **Recetas médicas:** documentos/datos sensibles; su manejo y almacenamiento requiere validación de Compliance y Seguridad.
- **Datos transaccionales del pedido:** trazabilidad y auditabilidad de cada pedido generado.

> No se incluye pasarela de pago en esta versión, por lo que **no** se manejan datos de tarjeta / pagos por ahora.

## 7. Criterios de éxito

- Un cliente puede realizar un pedido a través de la aplicación webapp (PWA).
- El cliente escoge el tipo de pago de su carrito de ventas.
- Se controla que exista stock en los productos para poder realizar el pedido.

## 8. Puntos Abiertos

1. **Contradicción: "escoger tipo de pago" vs exclusión de Pasarela de Pago.** El criterio de éxito indica que el cliente "escoge el tipo de pago de su carrito", pero el alcance excluye la pasarela de pago. Se debe definir qué se entiende por "tipo de pago" en esta versión (p. ej., pago contra entrega, retiro en tienda, efectivo/transferencia) y cómo se registra, sin pasarela.
   - **Qué falta:** definición de los tipos de pago soportados y su registro en el pedido.
   - **Quién resuelve:** Producto / Stakeholders.
   - **¿Bloquea?:** Sí, bloquea el inicio de la HU de generación de pedido/checkout.

2. **Gestión de recetas.** No se especifica cómo se solicita, adjunta o valida una receta para los medicamentos que la requieren, ni qué medicamentos requieren receta.
   - **Qué falta:** flujo de solicitud/validación de receta y listado de medicamentos que la requieren.
   - **Quién resuelve:** Compliance / Farmacéutico / Producto.
   - **¿Bloquea?:** No bloquea el catálogo ni el carrito, pero condiciona la HU de medicamentos con receta.

3. **Autenticación de clientes.** No se menciona si el cliente requiere login/registro para generar un pedido.
   - **Qué falta:** definición de autenticación/registro del cliente.
   - **Quién resuelve:** Producto / Seguridad.
   - **¿Bloquea?:** Condiciona las HUs de pedido y el manejo de datos personales.

4. **Gestión de stock / operario.** No se detalla si el ingreso de mercadería y la validación de stock son funcionalidades del mismo aplicativo PWA o de una herramienta aparte, ni cómo se expone la disponibilidad al cliente.
   - **Qué falta:** definición del alcance funcional de stock para el Operario y su relación con la validación de stock del cliente.
   - **Quién resuelve:** Producto / Operaciones.
   - **¿Bloquea?:** Condiciona la HU de validación de stock.
