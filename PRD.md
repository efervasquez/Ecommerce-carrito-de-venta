# Proyecto: Plataforma E-commerce - Botica la Luz

| Información General | Detalle |
| :--- | :--- |
| **Fecha de Creación** | 27 de Septiembre de 2026 |
| **Última Actualización** | 31 de Octubre de 2026 (Parámetros anti-abuso de reserva v1.8) |
| **Estado** | Aprobado / En Definición de HUs |
| **Autores** | Product Manager / Solutions Architect |
| **Público Objetivo** | Clientes recurrentes y nuevos de Botica la Luz |

---

## 1. Control de Versiones

* **v1.0 (27/09/2026):** Definición inicial del alcance del MVP, supuestos, criterios de éxito, automatización de recetas mediante OCR, flujos de devolución y logística de distribución propia.
* **v1.1 (04/10/2026):** Incorporación del módulo de autoregistro de clientes, lógica de persistencia de sesión vinculada al carrito, definición de pasarela de pruebas (Stripe Test), reglas del motor OCR, flujo detallado del buzón de despacho por estados y formalización de la matriz de reportería del Backoffice.
* **v1.2 (08/10/2026):** Actualización completa de flujos de negocio. Incorporación de recuperación de contraseñas por correo, lógica OCR síncrona con carrito/stock, marcas informativas en productos (ofertas, receta, precios bajos), buscador de scroll infinito sin paginación, vista de detalle extendida del producto, sección de ofertas en el carrito, reestructuración estricta del flujo físico de reclamos (límite de 3 intentos en campo), sin reembolsos, y adición del módulo de gestión manual de stock para contingencias ERP. Definición del RNF PA-07 (Concurrencia).
* **v1.3 (14/10/2026):** Revisión de consistencia. Reenumeración de RNF (PA-07 → RNF-01), adición de RF-06 (Pasarela de pagos) y RF-07 (Ciclo logístico), armonización de la disponibilidad con el KPI (99.5%), armonización de la redacción del límite de reintentos en RF-04.3 y formalización de la sección de Puntos Abiertos.
* **v1.4 (15/10/2026):** Actualización de seguridad derivada de la revisión adversarial. En RF-01.1 y Sección 3.1, se reemplaza el despacho de contraseñas provisionales en texto plano por el envío de enlaces seguros de activación de un solo uso con definición autónoma de contraseña por parte del cliente (ADR 0017).
* **v1.5 (31/10/2026):** Revisión de consistencia PRD ↔ HUs. Se corrige el Supuesto 3 de la Sección 7 (eliminada la referencia a "contraseñas provisionales", alineada a v1.4). Se incorpora a la Vista de Detalle del Producto (Sección 3.1) y a RF-02.3 el botón "Agregar al carrito" y un selector de cantidad.
* **v1.6 (31/10/2026):** Resolución formal de Puntos Abiertos (PA-01 a PA-05) por el Product Owner / Negocio: se define la reserva de stock a 24 horas con liberación automática por timeout/expiración (PA-01); se establece la asignación manual para la etiqueta "Precios bajos" (PA-02); se descarta la funcionalidad de inserción parcial ante stock mixto en OCR, suspendiendo la inserción completa si falta cualquier medicamento de la receta (PA-03); se formaliza el flujo de reclamos como sub-flujo posterior manual tras la entrega sin alterar los 4 estados base del pedido (PA-04); y se incorpora formalmente al alcance la Matriz de Reportería del Backoffice con la creación de RF-08 (PA-05).
* **v1.7 (31/10/2026):** Decisión de negocio sobre la reserva de stock por tipo de sesión (derivada de la revisión de ADR 0016 anti-abuso). Se define que el cliente **invitado (guest)** reserva stock únicamente al llegar al checkout, mientras que el cliente **autenticado** reserva al agregar al carrito; ambos con vigencia de 24 horas y liberación automática (PA-06).
* **v1.8 (31/10/2026):** Aprobación de los parámetros anti-abuso de reserva propuestos en el ADR 0016. Se fijan límites de cara al cliente (3 unidades por SKU, 10 productos por carrito guest) y controles técnicos (rate limit de 1 req/s con burst 5 al agregar al carrito, 3 inicios de checkout por minuto por IP, techo de 1 checkout guest activo con reservas o máximo 15 unidades reservadas por IP). Se formaliza mediante RF-03.6 y PA-07.

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
  * Permite al usuario realizar un auto-registro ingresando únicamente su correo electrónico; el sistema genera y despacha un enlace seguro de activación de un solo uso para que el cliente configure su propia contraseña de acceso de manera privada y protegida.
  * Control de sesión activa para mantener al cliente reconocido en la web.
  * **Recuperación de Contraseña:** Si el cliente olvida sus credenciales, el módulo dispondrá de una opción de recuperación. El sistema enviará una notificación por correo electrónico con un enlace de acceso directo que redirigirá al usuario a un formulario obligatorio de cambio de contraseña para restablecer su ingreso.

* **Catálogo Digital y Buscador Avanzado (Fuzzy Search):**
  * Búsqueda difusa (*Fuzzy Search*) tolerante a errores ortográficos o de tipeo (ej. mapear *"camiaa"* a *"camisa"*).
  * **Diseño de Interfaz sin Paginación:** Los productos se mostrarán en una lista continua de arriba a abajo (scroll infinito).
  * **Campos obligatorios en Tarjeta de Producto (Lista):** Cada ítem en el buscador debe mostrar: foto, nombre, componentes (principios activos), precio regular, descuentos por oferta (si aplica), una alerta visual si quedan menos de 6 unidades en stock o la etiqueta de "Precios bajos" (asignada manualmente por el operador), y un botón directo de "Agregar al carrito".

* **Vista de Detalle del Producto:**
  * Al hacer clic sobre cualquier producto de la lista, el sistema abrirá una página dedicada que contendrá: foto del producto, componentes, precio, indicador de si requiere receta médica, detalle del producto, presentación (empaque/ml/mg), métodos de entrega disponibles (Delivery o Retiro en la misma botica), contraindicaciones, precauciones/advertencias, reacciones adversas, y un botón de "Agregar al carrito" con selector de cantidad.

* **Reglas de Negocio y Atributos del Producto:**
  * **Venta restringida:** Cada producto de la botica contará con un flag/marca lógica que indique si "Necesita receta para la venta". Si no tiene activada esta marca, se considerará un producto de venta libre.
  * **Atributos comerciales:** Campos específicos para registrar si el producto está en oferta (con el valor porcentual correspondiente) y si cuenta con la etiqueta de "Precios bajos". La activación de la etiqueta "Precios bajos" es de carácter manual y se asigna directamente a cada producto por el operador en el catálogo/Backoffice (PA-02).

* **Carrito de Compras con Persistencia e Interfaz Orientada a Ofertas:**
  * Selección y reserva de productos ligada a la sesión del cliente con una vigencia máxima de 24 horas. Tras 24 horas de inactividad o expiración sin concretar la compra, el sistema libera automáticamente el stock reservado devolviéndolo al inventario disponible (PA-01).
  * **Regla de reserva por tipo de sesión:** el cliente **invitado (guest)** reserva stock únicamente al iniciar el checkout, mientras que el cliente **autenticado** reserva en el momento de agregar al carrito; ambos con TTL de 24 horas y liberación automática (PA-06).
  * **Parámetros anti-abuso de reserva (ADR 0016):** límite de **3 unidades por SKU** por carrito y **10 productos por carrito guest**; rate limit de **1 req/s con burst 5** al agregar al carrito; **3 inicios de checkout por minuto por IP**; techo de **1 checkout guest activo con reservas (o máximo 15 unidades reservadas) por IP** (PA-07).
  * **Sección Prioritaria:** Al ingresar a la vista del carrito de compras, la interfaz desplegará de forma obligatoria y en la parte superior todos los productos agregados que cuenten con ofertas activas.

* **Módulo OCR Automatizado para Recetas Médicas:**
  * Opción explícita "Leer receta" para que el cliente adjunte una foto o PDF del documento médico.
  * El sistema procesará el documento mediante OCR para determinar qué componente o marca de medicamento está solicitando el médico, cruzándolo de inmediato con la cantidad solicitada en la receta y el stock disponible.
  * **Flujo Automatizado Exitoso:** Una vez encontrados todos los medicamentos prescritos en la receta con existencias completas, el sistema los añadirá de forma automática y mostrará directamente el carrito de compras al cliente para que continúe el pago.
  * **Alertas de Quiebre y Descarte de Inserción Parcial:** En caso de que la botica no cuente con alguna medicina extraída por el OCR (o exista disponibilidad parcial con stock mixto), el sistema descartará la inserción parcial automática, suspenderá el ingreso de toda la receta al carrito y lanzará una alerta explícita indicando qué medicamentos no tienen stock disponible para que el cliente tome una decisión informada (PA-03).

* **Buzón de Despacho Logístico (Gestión de Pedidos):**
  * Centralización de órdenes confirmadas, consolidación de rutas por cercanía geográfica de zona y asignación a motorizados por orden de llegada o auto-asignación manual.
  * Ciclo de vida del pedido controlado por 4 estados obligatorios: *Registrado*, *Preparando producto*, *En camino* y *Entregado*.

* **Flujo de Reclamaciones por Mal Estado e Inmodificabilidad Transaccional:**
  * **Logística Inversa en Campo:** Ante un reclamo aprobado por producto en mal estado, la botica preparará un nuevo medicamento y lo enviará con un motorizado propio.
  * **Sub-flujo Posterior Manual:** Los reclamos por mal estado se gestionan como un sub-flujo operativo posterior, independiente y manual tras la entrega física del pedido. No alteran los 4 estados base de la orden (`Registrado`, `Preparando producto`, `En camino`, `Entregado`); una vez que el pedido pasa a estado *Entregado*, cualquier reclamo de cambio físico en campo se coordina mediante este procedimiento manual (PA-04).
  * **Validación en la entrega:** El motorizado exigirá físicamente al cliente el comprobante de pago original y verificará que el producto devuelto pertenezca efectivamente a "Botica la Luz" y se encuentre en mal estado. Solo tras cumplir esto entregará el nuevo artículo.
  * **Límite de Reintentos de Reclamo:** Si el nuevo producto entregado por el motorizado también presenta fallas o mal estado en el momento de la inspección física en campo, este paso se podrá repetir hasta un número máximo de 3 intentos adicionales.
  * **Política estricta de No Reembolso:** Todos los reclamos por mal estado se resolverán exclusivamente mediante cambio físico del producto. No existen reembolsos de dinero bajo ningún supuesto. Si el cliente manifiesta que se equivocó al realizar la compra, no habrá devolución de dinero ni cambios.

* **Módulo de Contingencia y Gestión Manual de Stock:**
  * Panel interno exclusivo para el registro manual de nuevos productos o la actualización inmediata de existencias (stock).
  * Este módulo actuará como mecanismo de tolerancia a fallos en caso de que la integración en línea con el ERP central sufra algún problema de conectividad. Permitirá registrar y modificar todos y cada uno de los campos de datos del producto descritos en este PRD (fotos, componentes, precios, marcas de receta, ofertas, contraindicaciones, etc.).

* **Pasarela de Pagos Integrada:**
  * Integración con Stripe en Modo Test (Sandbox) para el entorno MVP.

* **Módulo de Reportería del Backoffice:**
  * Panel de control y reportería para administradores y supervisores con indicadores clave de ventas, consolidado de pedidos por estado, reporte de productos de mayor rotación y alertas de quiebre de stock para reabastecimiento oportuno (PA-05).

### 3.2 Lo que NO INCLUYE (Fuera de Alcance)
* **Aplicación Móvil Nativa:** Operación exclusiva como Web App Responsive.
* **Consultas Médicas Online / Telemedicina.**
* **Devolución de dinero en efectivo o extornos:** Cláusula cerrada de cero reembolsos por error de cliente o insatisfacción.
* **Inserción parcial automática de recetas OCR con stock mixto:** Descartada la inserción parcial si falta stock de algún fármaco (PA-03).

---

## 4. Personas y Actores del Sistema
* **Cliente Final:** Usuario que gestiona su cuenta, recupera su clave vía mail, busca productos en la lista continua, adjunta recetas para compra directa automatizada por OCR, visualiza ofertas prioritarias en el carrito y recibe reposiciones bajo las reglas del motorizado.
* **Motorizado (Repartidor Propio):** Enlace logístico de campo con la facultad técnica y administrativa de validar comprobantes, verificar el origen del producto dañado, autorizar el cambio físico directo e iterar hasta un máximo de 3 intentos en caso de persistencia de fallos.
* **Administrador de Pedidos / Farmacéutico / Operador de Stock:** Supervisor que controla los despachos, procesa excepciones del catálogo, consulta reportes y métricas del Backoffice, y utiliza el módulo de contingencia manual para resguardar la exactitud del stock ante caídas de la API del ERP.

---

## 5. Requerimientos Funcionales

### RF-01: Módulo de Gestión de Usuarios y Accesos
* **RF-01.1:** El sistema permitirá el autoregistro rápido ingresando únicamente el correo electrónico, enviando un enlace seguro de activación de un solo uso que permitirá al usuario definir su propia contraseña de acceso.
* **RF-01.2:** El sistema dispondrá de un flujo de recuperación de contraseña que enviará un correo con un link único. Este link dirigirá a una interfaz donde se solicitará obligatoriamente la nueva contraseña para permitir el reingreso.

### RF-02: Catálogo y Experiencia de Usuario (UI/UX)
* **RF-02.1:** El motor de búsqueda implementará *Fuzzy Search* (búsqueda difusa) y renderizará los resultados de arriba a abajo en una sola lista sin paginación (scroll infinito).
* **RF-02.2:** La tarjeta del producto en la lista presentará de forma obligatoria: foto, nombre, componentes, precio, porcentaje de descuento por oferta (si aplica), alerta de stock bajo (< 6 unidades) o etiqueta de "Precios bajos" (asignada manualmente al producto), y el botón "Agregar al carrito".
* **RF-02.3:** Al hacer clic en un ítem, el sistema cargará una página detallada que incluirá: foto, componentes, precio, flag de receta requerida, detalle, presentación, métodos de entrega (delivery/retiro), contraindicaciones, precauciones/advertencias, reacciones adversas, y un botón "Agregar al carrito" con selector de cantidad.

### RF-03: Automatización OCR y Carrito de Compras
* **RF-03.1:** Al adjuntar una receta médica, el sistema extraerá mediante OCR los componentes/marcas y cantidades prescritas, consultará las existencias locales y, si todo está disponible, insertará los ítems y redirigirá directamente al usuario a la vista del carrito.
* **RF-03.2:** Si falta algún medicamento detectado por el OCR en el inventario (disponibilidad parcial o total ausencia), el sistema descartará la inserción parcial automática, detendrá la incorporación de la receta al carrito y mostrará una alerta explícita detallando la ausencia de stock de los productos afectados.
* **RF-03.3:** El sistema ordenará la interfaz del carrito de compras colocando todos los productos que tengan ofertas activas en la sección superior inicial de la pantalla.
* **RF-03.4:** El carrito mantendrá la reserva de inventario vinculada a la sesión por un lapso de 24 horas; al transcurrir dicho tiempo sin formalizar el pago, el sistema liberará automáticamente la reserva devolviendo las existencias al catálogo.
* **RF-03.5:** La reserva de stock se regirá por el tipo de sesión: el cliente **invitado (guest)** reservará únicamente al iniciar el checkout, mientras que el cliente **autenticado** reservará al agregar productos al carrito; en ambos casos la reserva expira y se libera automáticamente a las 24 horas (PA-06).
* **RF-03.6:** El sistema aplicará límites anti-abuso de reserva: máximo **3 unidades por SKU** por carrito y **10 productos por carrito guest**; limitará la adición al carrito a **1 req/s con burst 5**; limitará el inicio de checkout a **3 por minuto por IP**; y permitirá un techo de **1 checkout guest activo con reservas (o máximo 15 unidades reservadas) por IP** (PA-07).

### RF-04: Logística Inversa y Gestión de Reclamos
* **RF-04.1:** El sistema permitirá registrar reclamos por mal estado obligando a adjuntar la foto del producto dañado y el comprobante. Esto disparará la orden de despacho de un motorizado con un producto de reemplazo.
* **RF-04.2:** El sistema bloqueará cualquier opción de reembolso o devolución de dinero, tanto en la interfaz del cliente como en la del administrador.
* **RF-04.3:** El sistema permitirá registrar hasta un máximo de 3 intentos adicionales secuenciales de cambio en campo administrados por la hoja de ruta del motorizado antes de marcar la incidencia como escalada o cerrada.
* **RF-04.4:** El flujo de reclamos opera como un sub-flujo posterior manual e independiente una vez que la orden alcanza el estado `Entregado`, sin crear estados adicionales en el ciclo de vida del pedido.

### RF-05: Módulo de Stock Manual (Contingencia)
* **RF-05.1:** El Backoffice dispondrá de un módulo de inventario manual e independiente que permitirá dar de alta nuevos productos y actualizar la cantidad de stock de forma directa.
* **RF-05.2:** El módulo manual permitirá la edición total de la estructura de datos del producto descrita en este PRD (precios, ofertas, etiqueta manual de "Precios bajos", descripciones clínicas, requisitos de receta) para mitigar pérdidas de conexión con las APIs del ERP principal.

### RF-06: Pasarela de Pagos Integrada
* **RF-06.1:** El sistema integrará una pasarela de pagos mediante Stripe operando en Modo Test (Sandbox) para el entorno MVP.

### RF-07: Buzón de Despacho Logístico (Gestión de Pedidos)
* **RF-07.1:** El sistema centralizará las órdenes confirmadas y consolidará las rutas de despacho por cercanía geográfica de zona.
* **RF-07.2:** El sistema asignará los pedidos a motorizados por orden de llegada o mediante auto-asignación manual.
* **RF-07.3:** El ciclo de vida del pedido estará controlado por 4 estados obligatorios: `Registrado`, `Preparando producto`, `En camino` y `Entregado`.

### RF-08: Reportería y Métricas del Backoffice
* **RF-08.1:** El sistema dispondrá de un panel de reportería para el Backoffice que permitirá visualizar reportes consolidados de ventas y facturación en rangos de fechas seleccionables.
* **RF-08.2:** El panel presentará el balance de pedidos distribuidos por cada uno de los estados del ciclo de vida (`Registrado`, `Preparando producto`, `En camino`, `Entregado`).
* **RF-08.3:** El sistema generará reportes de inventario crítico, identificando productos con stock bajo (< 6 unidades), medicamentos con quiebres recurrentes y productos de mayor rotación comercial.

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
* El canal de mensajería (servidor SMTP) posee la capacidad para despachar inmediatamente enlaces seguros de activación de un solo uso y links de recuperación sin encolamientos.

---

## 8. Criterios de Éxito (KPIs a los 3 meses)

* **Eficiencia Operativa:** Disminución de un 30% en el volumen de atención manual (mensajes de WhatsApp y llamadas) para consultas de stock y cotizaciones.
* **Penetración Digital:** Lograr que al menos el 25% de la facturación global de la botica provenga del canal de ventas web.
* **Estabilidad del Sistema:** Mantener una disponibilidad mínima del 99.5% en la plataforma digital para asegurar la ventana de atención 24/7.

---

## 9. Puntos Abiertos (Resueltos)

Todos los puntos abiertos identificados en fases previas han sido definidos y cerrados formalmente por el Product Owner / Negocio el 31 de Octubre de 2026:

* **PA-01 — Reserva de stock:** **RESUELTO.** La duración de la sesión y reserva de stock queda establecida en **24 horas**. Transcurrido este lapso sin concretar la compra o por inactividad/timeout, el sistema libera automáticamente las unidades reservadas devolviéndolas al stock disponible.
* **PA-02 — Etiqueta "Precios bajos":** **RESUELTO.** La etiqueta es de asignación **manual**. El operador o farmacéutico la activa o desactiva directamente en la ficha del producto desde el catálogo/Backoffice.
* **PA-03 — OCR con stock mixto:** **RESUELTO.** Se **descarta la funcionalidad de inserción parcial**. Ante una receta con stock mixto (algunos medicamentos disponibles y otros no), el sistema suspende la inserción completa de la receta al carrito y alerta explícitamente al cliente los ítems faltantes para evitar compras incompletas inadvertidas.
* **PA-04 — Reclamos en el ciclo de vida:** **RESUELTO.** Los reclamos por mal estado se gestionan como un **sub-flujo posterior manual** tras la recepción del pedido en estado `Entregado`. No se crean estados adicionales en la máquina de estados de pedidos de la plataforma.
* **PA-05 — Reportería del Backoffice:** **RESUELTO.** Se **incorpora formalmente al alcance** del MVP, formalizado a través del requerimiento funcional **RF-08: Reportería y Métricas del Backoffice**.
* **PA-06 — Reserva de stock por tipo de sesión:** **RESUELTO.** Derivada de la revisión del ADR 0016 (anti-abuso de carrito guest). El cliente **invitado (guest)** reserva stock únicamente al iniciar el checkout, mientras que el cliente **autenticado** reserva al agregar al carrito; ambos con TTL de 24 horas y liberación automática. Se formaliza mediante el requerimiento **RF-03.5**.
* **PA-07 — Parámetros anti-abuso de reserva:** **RESUELTO.** Se aprueban los límites propuestos en el ADR 0016: **3 unidades por SKU** y **10 productos por carrito guest** (límites de cara al cliente); rate limit de **1 req/s con burst 5** al agregar, **3 inicios de checkout por minuto por IP** y techo de **1 checkout guest activo con reservas (o máx. 15 unidades) por IP** (controles técnicos). Se formaliza mediante el requerimiento **RF-03.6**.

---

## 10. Próximo paso

Entrega formal al Agente BA para la actualización de las Historias de Usuario afectadas:
1. Actualizar [HU-03](file:///C:/Temp2/Ecommerce-carrito-de-venta/HUs/HU-03-busqueda-difusa-y-catalogo-scroll-infinito.md) y [HU-04](file:///C:/Temp2/Ecommerce-carrito-de-venta/HUs/HU-04-vista-detalle-extendida-producto.md) con la asignación manual de "Precios bajos" (PA-02).
2. Actualizar [HU-05](file:///C:/Temp2/Ecommerce-carrito-de-venta/HUs/HU-05-carrito-compras-persistencia-y-ofertas.md) con la reserva de 24 horas y regla de expiración (PA-01).
3. Actualizar [HU-06](file:///C:/Temp2/Ecommerce-carrito-de-venta/HUs/HU-06-automatizacion-ocr-recetas-medicas.md) con el descarte de inserción parcial ante stock mixto (PA-03).
4. Actualizar [HU-08](file:///C:/Temp2/Ecommerce-carrito-de-venta/HUs/HU-08-buzon-despacho-logistico-y-ciclo-vida-pedidos.md) y [HU-09](file:///C:/Temp2/Ecommerce-carrito-de-venta/HUs/HU-09-logistica-inversa-reclamos-y-cambio-fisico.md) clarificando el sub-flujo posterior manual tras la entrega (PA-04).
5. Redactar la nueva **HU-11: Reportería y Métricas del Backoffice** derivada de RF-08 (PA-05).
6. Actualizar [HU-05](file:///C:/Temp2/Ecommerce-carrito-de-venta/HUs/HU-05-carrito-compras-persistencia-y-ofertas.md) con la regla de reserva por tipo de sesión (guest en checkout / autenticado al agregar) derivada de PA-06/RF-03.5, y los parámetros anti-abuso derivados de PA-07/RF-03.6.
