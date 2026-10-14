# Proyecto: Plataforma E-commerce - Botica la Luz

| Información General | Detalle |
| :--- | :--- |
| **Fecha de Creación** | 27 de Septiembre de 2026 |
| **Última Actualización** | 14 de Octubre de 2026 (Revisión de consistencia) |
| **Estado** | En Revisión |
| **Autores** | Product Manager / Solutions Architect |
| **Público Objetivo** | Clientes recurrentes y nuevos de Botica la Luz |

---

## 1. Control de Versiones

* **v1.0 (27/09/2026):** Definición inicial del alcance del MVP, supuestos, criterios de éxito, automatización de recetas mediante OCR, flujos de devolución y logística de distribución propia.
* **v1.1 (04/10/2026):** Incorporación del módulo de autoregistro de clientes, lógica de persistencia de sesión vinculada al carrito, definición de pasarela de pruebas (Stripe Test), reglas del motor OCR, flujo detallado del buzón de despacho por estados y formalización de la matriz de reportería del Backoffice.
* **v1.2 (08/10/2026):** Actualización completa de flujos de negocio. Incorporación de recuperación de contraseñas por correo, lógica OCR síncrona con carrito/stock, marcas informativas en productos (ofertas, receta, precios bajos), buscador de scroll infinito sin paginación, vista de detalle extendida del producto, sección de ofertas en el carrito, reestructuración estricta del flujo físico de reclamos (límite de 3 intentos en campo), sin reembolsos, y adición del módulo de gestión manual de stock para contingencias ERP. Definición del RNF PA-07 (Concurrencia).
* **v1.3 (14/10/2026):** Revisión de consistencia. Reenumeración de RNF (PA-07 → RNF-01), adición de RF-06 (Pasarela de pagos) y RF-07 (Ciclo logístico), armonización de la disponibilidad con el KPI (99.5%), armonización de la redacción del límite de reintentos en RF-04.3 y formalización de la sección de Puntos Abiertos.

---

## 2. Introducción, Problema y Objetivos

### 2.1 Problema Comercial
Botica la Luz procesa todas sus ventas de medicamentos e insumos de manera presencial o mediante interacciones manuales por llamadas y WhatsApp. Este modelo limita la atención al horario comercial físico, genera cuellos de botella operativos y provoca pérdidas de ventas debido al tiempo de espera en la respuesta de los canales digitales actuales.

### 2.2 Objetivos Estratégicos
* Digitalizar la experiencia del cliente mediante un carrito de compras interactivo con atención automatizada 24/7.
* Reducir la fricción y el tiempo de atención, permitiendo que el usuario autogestione la búsqueda de existencias y sus compras sin depender de asistencia telefónica o presencial.

---

## 3. Alcance del Proyecto (Scope)

### 3.1 Lo que INCLUYE (MVP)

* **Módulo de Autoregistro, Autenticación y Recuperación:**
  * Permite al usuario realizar un auto-registro ingresando únicamente su correo electrónico; el sistema genera y envía una contraseña provisional de forma automática.
  * Control de sesión activa para mantener al cliente reconocido en la web.
  * **Recuperación de Contraseña:** Si el cliente olvida sus credenciales, el módulo dispondrá de una opción de recuperación. El sistema enviará una notificación por correo electrónico con un enlace de acceso directo que redirigirá al usuario a un formulario obligatorio de cambio de contraseña para restablecer su ingreso.

* **Catálogo Digital y Buscador Avanzado (Fuzzy Search):**
  * Búsqueda difusa (*Fuzzy Search*) tolerante a errores ortográficos o de tipeo (ej. mapear *"camiaa"* a *"camisa"*).
  * **Diseño de Interfaz sin Paginación:** Los productos se mostrarán en una lista continua de arriba a abajo (scroll infinito).
  * **Campos obligatorios en Tarjeta de Producto (Lista):** Cada ítem en el buscador debe mostrar: foto, nombre, componentes (principios activos), precio regular, descuentos por oferta (si aplica), una alerta visual si quedan menos de 6 unidades en stock o la etiqueta de "Precios bajos", y un botón directo de "Agregar al carrito".

* **Vista de Detalle del Producto:**
  * Al hacer clic sobre cualquier producto de la lista, el sistema abrirá una página dedicada que contendrá: foto del producto, componentes, precio, indicador de si requiere receta médica, detalle del producto, presentación (empaque/ml/mg), métodos de entrega disponibles (Delivery o Retiro en la misma botica), contraindicaciones, precauciones/advertencias y reacciones adversas.

* **Reglas de Negocio y Atributos del Producto:**
  * **Venta restringida:** Cada producto de la botica contará con un flag/marca lógica que indique si "Necesita receta para la venta". Si no tiene activada esta marca, se considerará un producto de venta libre.
  * **Atributos comerciales:** Campos específicos para registrar si el producto está en oferta (con el valor porcentual correspondiente) y si cuenta con la etiqueta de "Precios bajos".

* **Carrito de Compras con Persistencia e Interfaz Orientada a Ofertas:**
  * Selección y reserva de productos ligada estrictamente a la duración de la sesión del cliente.
  * **Sección Prioritaria:** Al ingresar a la vista del carrito de compras, la interfaz desplegará de forma obligatoria y en la parte superior todos los productos agregados que cuenten con ofertas activas.

* **Módulo OCR Automatizado para Recetas Médicas:**
  * Opción explícita "Leer receta" para que el cliente adjunte una foto o PDF del documento médico.
  * El sistema procesará el documento mediante OCR para determinar qué componente o marca de medicamento está solicitando el médico, cruzándolo de inmediato con la cantidad solicitada en la receta y el stock disponible.
  * **Flujo Automatizado Exitoso:** Una vez encontrados los medicamentos de la receta, el sistema los añadirá de forma automática y mostrará directamente el carrito de compras al cliente para que continúe el pago.
  * **Alertas de Quiebre:** En caso de que la botica no cuente con alguna medicina extraída por el OCR, el sistema suspenderá la inserción automática y lanzará una alerta explícita indicando que no hay stock de ese medicamento en específico.

* **Buzón de Despacho Logístico (Gestión de Pedidos):**
  * Centralización de órdenes confirmadas, consolidación de rutas por cercanía geográfica de zona y asignación a motorizados por orden de llegada o auto-asignación manual.
  * Ciclo de vida del pedido controlado por 4 estados obligatorios: *Registrado*, *Preparando producto*, *En camino* y *Entregado*.

* **Flujo de Reclamaciones por Mal Estado e Inmodificabilidad Transaccional:**
  * **Logística Inversa en Campo:** Ante un reclamo aprobado por producto en mal estado, la botica preparará un nuevo medicamento y lo enviará con un motorizado propio.
  * **Validación en la entrega:** El motorizado exigirá físicamente al cliente el comprobante de pago original y verificará que el producto devuelto pertenezca efectivamente a "Botica la Luz" y se encuentre en mal estado. Solo tras cumplir esto entregará el nuevo artículo.
  * **Límite de Reintentos de Reclamo:** Si el nuevo producto entregado por el motorizado también presenta fallas o mal estado en el momento de la inspección física en campo, este paso se podrá repetir hasta un número máximo de 3 intentos adicionales.
  * **Política estricta de No Reembolso:** Todos los reclamos por mal estado se resolverán exclusivamente mediante cambio físico del producto. No existen reembolsos de dinero bajo ningún supuesto. Si el cliente manifiesta que se equivocó al realizar la compra, no habrá devolución de dinero ni cambios.

* **Módulo de Contingencia y Gestión Manual de Stock:**
  * Panel interno exclusivo para el registro manual de nuevos productos o la actualización inmediata de existencias (stock).
  * Este módulo actuará como mecanismo de tolerancia a fallos en caso de que la integración en línea con el ERP central sufra algún problema de conectividad. Permitirá registrar y modificar todos y cada uno de los campos de datos del producto descritos en este PRD (fotos, componentes, precios, marcas de receta, ofertas, contraindicaciones, etc.).

* **Pasarela de Pagos Integrada:**
  * Integración con Stripe en Modo Test (Sandbox) para el entorno MVP.

### 3.2 Lo que NO INCLUYE (Fuera de Alcance)
* **Aplicación Móvil Nativa:** Operación exclusiva como Web App Responsive.
* **Consultas Médicas Online / Telemedicina.**
* **Devolución de dinero en efectivo o extornos:** Cláusula cerrada de cero reembolsos por error de cliente o insatisfacción.

---

## 4. Personas y Actores del Sistema
* **Cliente Final:** Usuario que gestiona su cuenta, recupera su clave vía mail, busca productos en la lista continua, adjunta recetas para compra directa automatizada por OCR, visualiza ofertas prioritarias en el carrito y recibe reposiciones bajo las reglas del motorizado.
* **Motorizado (Repartidor Propio):** Enlace logístico de campo con la facultad técnica y administrativa de validar comprobantes, verificar el origen del producto dañado, autorizar el cambio físico directo e iterar hasta un máximo de 3 intentos en caso de persistencia de fallos.
* **Administrador de Pedidos / Farmacéutico / Operador de Stock:** Supervisor que controla los despachos, procesa excepciones del catálogo y utiliza el módulo de contingencia manual para resguardar la exactitud del stock ante caídas de la API del ERP.

---

## 5. Requerimientos Funcionales

### RF-01: Módulo de Gestión de Usuarios y Accesos
* **RF-01.1:** El sistema permitirá el autoregistro rápido ingresando únicamente el correo electrónico, enviando una contraseña provisional de manera automatizada.
* **RF-01.2:** El sistema dispondrá de un flujo de recuperación de contraseña que enviará un correo con un link único. Este link dirigirá a una interfaz donde se solicitará obligatoriamente la nueva contraseña para permitir el reingreso.

### RF-02: Catálogo y Experiencia de Usuario (UI/UX)
* **RF-02.1:** El motor de búsqueda implementará *Fuzzy Search* (búsqueda difusa) y renderizará los resultados de arriba a abajo en una sola lista sin paginación (scroll infinito).
* **RF-02.2:** La tarjeta del producto en la lista presentará de forma obligatoria: foto, nombre, componentes, precio, porcentaje de descuento por oferta (si aplica), alerta de stock bajo (< 6 unidades) o etiqueta de "Precios bajos", y el botón "Agregar al carrito".
* **RF-02.3:** Al hacer clic en un ítem, el sistema cargará una página detallada que incluirá: foto, componentes, precio, flag de receta requerida, detalle, presentación, métodos de entrega (delivery/retiro), contraindicaciones, precauciones/advertencias y reacciones adversas.

### RF-03: Automatización OCR y Carrito de Compras
* **RF-03.1:** Al adjuntar una receta médica, el sistema extraerá mediante OCR los componentes/marcas y cantidades prescritas, consultará las existencias locales y, si todo está disponible, insertará los ítems y redirigirá directamente al usuario a la vista del carrito.
* **RF-03.2:** Si falta algún medicamento detectado por el OCR en el inventario, el sistema detendrá el proceso y mostrará una alerta explícita indicando la ausencia de stock de dicho producto.
* **RF-03.3:** El sistema ordenará la interfaz del carrito de compras colocando todos los productos que tengan ofertas activas en la sección superior inicial de la pantalla.

### RF-04: Logística Inversa y Gestión de Reclamos
* **RF-04.1:** El sistema permitirá registrar reclamos por mal estado obligando a adjuntar la foto del producto dañado y el comprobante. Esto disparará la orden de despacho de un motorizado con un producto de reemplazo.
* **RF-04.2:** El sistema bloqueará cualquier opción de reembolso o devolución de dinero, tanto en la interfaz del cliente como en la del administrador.
* **RF-04.3:** El sistema permitirá registrar hasta un máximo de 3 intentos adicionales secuenciales de cambio en campo administrados por la hoja de ruta del motorizado antes de marcar la incidencia como escalada o cerrada.

### RF-05: Módulo de Stock Manual (Contingencia)
* **RF-05.1:** El Backoffice dispondrá de un módulo de inventario manual e independiente que permitirá dar de alta nuevos productos y actualizar la cantidad de stock de forma directa.
* **RF-05.2:** El módulo manual permitirá la edición total de la estructura de datos del producto descrita en este PRD (precios, ofertas, descripciones clínicas, requisitos de receta) para mitigar pérdidas de conexión con las APIs del ERP principal.

### RF-06: Pasarela de Pagos Integrada
* **RF-06.1:** El sistema integrará una pasarela de pagos mediante Stripe operando en Modo Test (Sandbox) para el entorno MVP.

### RF-07: Buzón de Despacho Logístico (Gestión de Pedidos)
* **RF-07.1:** El sistema centralizará las órdenes confirmadas y consolidará las rutas de despacho por cercanía geográfica de zona.
* **RF-07.2:** El sistema asignará los pedidos a motorizados por orden de llegada o mediante auto-asignación manual.
* **RF-07.3:** El ciclo de vida del pedido estará controlado por 4 estados obligatorios: `Registrado`, `Preparando producto`, `En camino` y `Entregado`.

---

## 6. Requerimientos No Funcionales

### RNF-01: Rendimiento y Concurrencia de la Plataforma
* **Métrica de Carga Concurrente:** El sistema deberá garantizar un rendimiento óptimo y estable con una carga sostenida de hasta 250 clientes conectados de forma simultánea, realizando operaciones críticas en paralelo como solicitudes de pedidos, búsquedas difusas en el catálogo o la carga y procesamiento de recetas médicas mediante el motor OCR.
* **Tiempo de Respuesta:** Bajo la máxima carga concurrente estipulada (250 usuarios), el tiempo de respuesta del servidor para búsquedas y procesamiento de carritos no deberá exceder los 2.5 segundos.

### RNF-02: Seguridad y Privacidad de Datos
* **Cifrado y LPDP:** Implementación de cifrado SSL/TLS para la transferencia de datos y cumplimiento estricto con la Ley de Protección de Datos Personales (LPDP) de Perú al procesar recetas médicas e historiales de compra.

### RNF-03: Disponibilidad (Uptime)
* **Operación Continua:** Disponibilidad de la plataforma web 24/7 para el autoregistro, búsqueda y pasarela transaccional, con un objetivo de disponibilidad mínima del 99.5% alineado al KPI de la Sección 8.

---

## 7. Supuestos del Proyecto (Assumptions)

* El ERP de la botica cuenta con la infraestructura para soportar las consultas en línea y decrementos de stock concurrentes.
* El motor OCR mantiene un tiempo de procesamiento base estable para no degradar la experiencia de usuario durante la carga concurrente masiva.
* El canal de mensajería (servidor SMTP) posee la capacidad para despachar inmediatamente correos de contraseñas provisionales y links de recuperación sin encolamientos.

---

## 8. Criterios de Éxito (KPIs a los 3 meses)

* **Eficiencia Operativa:** Disminución de un 30% en el volumen de atención manual (mensajes de WhatsApp y llamadas) para consultas de stock y cotizaciones.
* **Penetración Digital:** Lograr que al menos el 25% de la facturación global de la botica provenga del canal de ventas web.
* **Estabilidad del Sistema:** Mantener una disponibilidad mínima del 99.5% en la plataforma digital para asegurar la ventana de atención 24/7.

---

## 9. Puntos Abiertos

* **PA-01 — Reserva de stock:** ¿Cuál es la duración exacta de la sesión/reserva de stock y la regla de liberación automática (inactividad, abandono o timeout)?
* **PA-02 — Etiqueta "Precios bajos":** ¿Qué criterio activa la etiqueta "Precios bajos" en un producto?
* **PA-03 — OCR con stock mixto:** Ante una receta con medicamentos con y sin stock disponible, ¿el sistema inserta los productos disponibles y alerta solo los faltantes, o suspende la inserción de toda la receta?
* **PA-04 — Reclamos en el ciclo de vida:** ¿El flujo de reclamos por mal estado debe reflejarse con uno o más estados adicionales en el ciclo de vida del pedido, o se gestiona como un sub-flujo independiente posterior a la entrega?
* **PA-05 — Reportería del Backoffice:** El changelog v1.1 menciona la "matriz de reportería del Backoffice" que no figura en el Alcance. ¿Se incorpora al alcance (y se define su RF) o se elimina la mención del changelog?

## 10. Próximo paso

Entrega al Agente BA para validación previa de consistencia y redacción de Historias de Usuario. Los Puntos Abiertos (PA-01 a PA-05) deben quedar reflejados en cada HU afectada.

