# HU-01: Autoregistro rápido y autenticación de clientes mediante enlace seguro de activación

## Historia de usuario
Como Cliente Final  
Quiero registrarme en la plataforma ingresando únicamente mi correo electrónico y recibir un enlace seguro de activación de un solo uso  
Para definir mi propia contraseña de acceso de manera privada y acceder rápidamente al e-commerce, manteniendo mi sesión reconocida y gestionando mis compras de medicamentos e insumos de forma digital 24/7.

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance (3.1 Lo que INCLUYE — Módulo de Autoregistro, Autenticación y Recuperación), 4. Personas y Actores (Cliente Final), 5. Requerimientos Funcionales (RF-01: Módulo de Gestión de Usuarios y Accesos — RF-01.1).
- **Requerimientos Funcionales asociados:** RF-01.1 (*El sistema permitirá el autoregistro rápido ingresando únicamente el correo electrónico, enviando un enlace seguro de activación de un solo uso que permitirá al usuario definir su propia contraseña de acceso*).
- **Criterios de éxito y RNF asociados:** RNF-02 (*Seguridad y Privacidad de Datos / LPDP Perú, generación y almacenamiento cifrado de credenciales*), RNF-03 (*Disponibilidad 24/7 con objetivo mínimo de 99.5%*), Criterio de éxito — Estabilidad del Sistema (*Disponibilidad mínima del 99.5% 24/7 según Sección 8 del PRD*), Supuesto 3 (*Servidor SMTP con capacidad de despacho inmediato de enlaces de activación y recuperación sin encolamientos*).
- **Cobertura:** Formulario web de autoregistro con campo único de correo electrónico, generación y despacho de un enlace seguro de activación de un solo uso por correo electrónico, definición autónoma y privada de la contraseña por parte del cliente, autenticación de usuario y control de sesión activa persistente.

## Criterios de aceptación funcionales
1. **Formulario simplificado de autoregistro:** La interfaz de registro solicita únicamente el correo electrónico del cliente. No se exige el llenado previo de nombres, documentos de identidad, teléfonos ni contraseñas manuales en este paso inicial.
2. **Generación y despacho de enlace seguro de activación:** Al procesar la solicitud, el sistema genera un enlace seguro de activación de un solo uso y lo envía al correo electrónico proporcionado. No se despacha ninguna contraseña provisional en texto plano.
3. **Definición autónoma de contraseña:** Al abrir el enlace de activación, el cliente es redirigido a un formulario obligatorio donde define su propia contraseña de acceso de manera privada y protegida, completando así la creación de su cuenta.
4. **Control y persistencia de sesión:** Una vez activada la cuenta, el sistema autentica al usuario, genera un token seguro y mantiene la sesión del cliente activa y reconocida a lo largo de su navegación en la aplicación web, asociándola a su carrito de compras.
5. **Validación de formato y duplicados:**
   - Si el formato del correo ingresado no es válido (ej. sin `@` o dominio incompleto), el sistema detiene el proceso y muestra un mensaje de advertencia visual.
   - Si el correo ya se encuentra registrado previamente en el sistema, se rechaza la creación de una cuenta duplicada y se orienta al usuario hacia el inicio de sesión o al flujo de recuperación de contraseña.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Autoregistro exitoso con correo electrónico y definición autónoma de contraseña
```gherkin
Feature: Autoregistro de clientes
  Scenario: Cliente nuevo se registra únicamente con su correo electrónico
    Given que el usuario no autenticado se encuentra en la pantalla de registro de Botica la Luz
    When ingresa su correo electrónico "cliente.nuevo@ejemplo.com"
    And pulsa el botón "Registrarme"
    Then el sistema crea la cuenta de usuario en estado pendiente de activación
    And genera y envía un enlace seguro de activación de un solo uso a "cliente.nuevo@ejemplo.com"
    And muestra un mensaje en pantalla indicando que se envió un enlace de activación a su correo
    When el cliente abre el enlace y define su propia contraseña "MiClaveSegura2026!"
    Then el sistema activa la cuenta y confirma el registro exitoso
```

### Escenario 2 — Caso borde: Intento de registro con formato de correo electrónico inválido
```gherkin
Feature: Autoregistro de clientes
  Scenario: Usuario ingresa un correo con formato erróneo
    Given que el usuario se encuentra en el formulario de registro rápido
    When ingresa el texto "correo_sin_dominio.com" en el campo de correo electrónico
    And intenta enviar el formulario
    Then el sistema bloquea el envío de la solicitud
    And no genera ningún enlace de activación ni registra un nuevo usuario
    And resalta el campo de texto con un mensaje indicando que el formato del correo es inválido
```

## Supuestos
- **Validación y unicidad de correo:** Se asume como regla funcional y técnica estándar (derivada de RNF-02, LPDP y seguridad de cuentas en AGENTS.md) que el correo electrónico debe validar formato RFC y unicidad en la base de datos para evitar colisiones de cuentas y garantizar la entrega efectiva del enlace de activación.

## Puntos Abiertos (Resueltos)
- **PA-01 — Reserva de stock:** RESUELTO (31/10/2026). La sesión activa asociada al carrito de compras mantiene la reserva de inventario por un lapso máximo de **24 horas**. Transcurrido ese tiempo sin formalizar el pago (o por inactividad/timeout), el sistema libera automáticamente el stock reservado.

## Exclusiones ("No incluye")
- **Aplicación Móvil Nativa:** El registro opera de manera exclusiva sobre la Web App Responsive para navegadores (Sección 3.2 del PRD).
- **Registro mediante proveedores OAuth de terceros:** No incluye inicio de sesión federado con Google, Facebook ni Apple en el MVP.
- **Validación de identidad o verificación por SMS/WhatsApp:** El canal de despacho del enlace de activación se limita estrictamente a correo electrónico (SMTP).
