# HU-01: Autoregistro rápido y autenticación de clientes con contraseña provisional

## Historia de usuario
Como Cliente Final  
Quiero registrarme en la plataforma ingresando únicamente mi correo electrónico y recibir de forma automática una contraseña provisional  
Para acceder rápidamente al e-commerce, mantener mi sesión reconocida y gestionar mis compras de medicamentos e insumos de forma digital 24/7.

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance (3.1 Lo que INCLUYE — Módulo de Autoregistro, Autenticación y Recuperación), 4. Personas y Actores (Cliente Final), 5. Requerimientos Funcionales (RF-01: Módulo de Gestión de Usuarios y Accesos — RF-01.1).
- **Requerimientos Funcionales asociados:** RF-01.1 (*El sistema permitirá el autoregistro rápido ingresando únicamente el correo electrónico, enviando una contraseña provisional de manera automatizada*).
- **Criterios de éxito y RNF asociados:** RNF-02 (*Seguridad y Privacidad de Datos / LPDP Perú, generación y almacenamiento cifrado de credenciales*), RNF-03 (*Disponibilidad 24/7 con objetivo mínimo de 99.5%*), Supuesto 3 (*Servidor SMTP con capacidad de despacho inmediato sin encolamientos*).
- **Cobertura:** Formulario web de autoregistro con campo único de correo electrónico, generación aleatoria y segura de contraseña provisional por el backend, despacho inmediato por correo electrónico, autenticación de usuario y control de sesión activa persistente con rol de Cliente Final (RBAC).

## Criterios de aceptación funcionales
1. **Formulario simplificado de autoregistro:** La interfaz de registro solicita únicamente el correo electrónico del cliente. No se exige el llenado previo de nombres, documentos de identidad, teléfonos ni contraseñas manuales en este paso inicial.
2. **Generación automática de contraseña provisional:** Al procesar la solicitud, el sistema genera de forma desasistida una contraseña temporal segura y la asigna a la nueva cuenta de usuario creada en estado activo.
3. **Despacho inmediato de credenciales:** El sistema envía un correo electrónico al buzón proporcionado con la contraseña provisional e instrucciones claras de acceso a la tienda virtual.
4. **Control y persistencia de sesión:** Una vez ingresadas las credenciales (correo y clave provisional), el sistema autentica al usuario, genera un token seguro y mantiene la sesión del cliente activa y reconocida a lo largo de su navegación en la aplicación web, asociándola a su carrito de compras.
5. **Validación de formato y duplicados:**
   - Si el formato del correo ingresado no es válido (ej. sin `@` o dominio incompleto), el sistema detiene el proceso y muestra un mensaje de advertencia visual.
   - Si el correo ya se encuentra registrado previamente en el sistema, se rechaza la creación de una cuenta duplicada y se orienta al usuario hacia el inicio de sesión o al flujo de recuperación de contraseña.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Autoregistro exitoso con correo electrónico y recepción de contraseña provisional
```gherkin
Feature: Autoregistro de clientes
  Scenario: Cliente nuevo se registra únicamente con su correo electrónico
    Given que el usuario no autenticado se encuentra en la pantalla de registro de Botica la Luz
    When ingresa su correo electrónico "cliente.nuevo@ejemplo.com"
    And pulsa el botón "Registrarme"
    Then el sistema crea la cuenta de usuario con rol de Cliente Final
    And genera una contraseña provisional segura
    And envía un correo electrónico a "cliente.nuevo@ejemplo.com" conteniendo la contraseña provisional
    And muestra un mensaje en pantalla indicando que sus credenciales fueron enviadas a su correo
```

### Escenario 2 — Caso borde: Intento de registro con formato de correo electrónico inválido
```gherkin
Feature: Autoregistro de clientes
  Scenario: Usuario ingresa un correo con formato erróneo
    Given que el usuario se encuentra en el formulario de registro rápido
    When ingresa el texto "correo_sin_dominio.com" en el campo de correo electrónico
    And intenta enviar el formulario
    Then el sistema bloquea el envío de la solicitud
    And no genera ninguna contraseña provisional ni registra un nuevo usuario
    And resalta el campo de texto con un mensaje indicando que el formato del correo es inválido
```

## Puntos Abiertos
- Sin puntos abiertos pendientes en este requerimiento. Todas las definiciones funcionales se encuentran confirmadas en el PRD (RF-01.1).

## Exclusiones ("No incluye")
- **Aplicación Móvil Nativa:** El registro opera de manera exclusiva sobre la Web App Responsive para navegadores (Sección 3.2 del PRD).
- **Registro mediante proveedores OAuth de terceros:** No incluye inicio de sesión federado con Google, Facebook ni Apple en el MVP.
- **Validación de identidad o verificación por SMS/WhatsApp:** El canal de despacho de credenciales provisionales se limita estrictamente a correo electrónico (SMTP).
