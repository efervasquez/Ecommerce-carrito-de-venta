# HU-02: Recuperación de contraseña por correo electrónico con enlace directo y formulario obligatorio

## Historia de usuario
Como Cliente Final  
Quiero solicitar la recuperación de mi contraseña ingresando mi correo electrónico y recibir un enlace de acceso directo  
Para acceder a un formulario obligatorio donde pueda definir una nueva contraseña y restablecer mi ingreso seguro a la plataforma.

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance (3.1 Lo que INCLUYE — Módulo de Autoregistro, Autenticación y Recuperación), 4. Personas y Actores (Cliente Final), 5. Requerimientos Funcionales (RF-01: Módulo de Gestión de Usuarios y Accesos — RF-01.2).
- **Requerimientos Funcionales asociados:** RF-01.2 (*El sistema dispondrá de un flujo de recuperación de contraseña que enviará un correo con un link único. Este link dirigirá a una interfaz donde se solicitará obligatoriamente la nueva contraseña para permitir el reingreso*).
- **Criterios de éxito y RNF asociados:** RNF-02 (*Seguridad y Privacidad de Datos / Tokens de un solo uso y caducidad temporal según LPDP*), Supuesto 3 (*Servidor SMTP con despacho inmediato de correos sin encolamientos*).
- **Cobertura:** Opción de recuperación "¿Olvidaste tu contraseña?" en el formulario de inicio de sesión, validación de cuenta existente, emisión y envío de enlace directo con token único criptográfico vía correo electrónico, redirección al formulario exclusivo y obligatorio de cambio de clave, invalidación del enlace tras su uso y actualización de credenciales.

## Criterios de aceptación funcionales
1. **Acceso a la opción de recuperación:** La pantalla de autenticación dispone de un enlace visible "¿Olvidaste tu contraseña?" que dirige al usuario a una interfaz donde solo debe ingresar su correo electrónico registrado.
2. **Generación y despacho de enlace único:** Al enviar la solicitud con un correo existente, el sistema genera un token de un solo uso con expiración temporal y envía un correo electrónico al usuario con un enlace directo a la pantalla de restablecimiento.
3. **Formulario obligatorio de nueva contraseña:**
   - Al pulsar sobre el enlace recibido en el correo, la aplicación web redirige al usuario de forma obligatoria a un formulario exclusivo de cambio de contraseña.
   - El sistema no permite navegar hacia ninguna otra sección de la tienda ni autenticarse en segundo plano hasta que el cliente ingrese y confirme satisfactoriamente su nueva contraseña.
4. **Invalidación de token e inicio de sesión:**
   - Al confirmar la nueva contraseña, el sistema actualiza de manera segura el hash de la clave en la base de datos e invalida permanentemente el token del enlace utilizado.
   - El sistema confirma el cambio exitoso y redirige al usuario a la pantalla de inicio de sesión o inicia su sesión activa de manera segura.
5. **Control de enlaces inválidos o expirados:** Si el cliente hace clic en un enlace cuyo token ya expiró o ya fue utilizado previamente, el sistema muestra un mensaje de error claro y bloquea el formulario de cambio, orientando a generar una nueva solicitud.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Restablecimiento exitoso de contraseña mediante enlace de correo
```gherkin
Feature: Recuperación de contraseña de clientes
  Scenario: Cliente restablece su contraseña mediante el enlace recibido por correo
    Given que el cliente registrado "cliente.activo@ejemplo.com" olvidó su contraseña
    And solicitó la recuperación desde la pantalla de login
    When el cliente abre el correo electrónico recibido de Botica la Luz
    And hace clic en el enlace único de recuperación
    Then el sistema lo redirige al formulario obligatorio de nueva contraseña
    When el cliente ingresa su nueva contraseña "MiClaveSegura2026!" en ambos campos de confirmación
    And pulsa el botón "Actualizar contraseña"
    Then el sistema actualiza la contraseña en la base de datos
    And invalida el enlace de recuperación utilizado
    And muestra un mensaje de confirmación de restablecimiento exitoso
```

### Escenario 2 — Caso borde: Intento de reutilización de un enlace de recuperación ya consumido
```gherkin
Feature: Recuperación de contraseña de clientes
  Scenario: Cliente intenta abrir un enlace de recuperación previamente utilizado
    Given que el cliente ya restableció su contraseña exitosamente con un enlace previo
    When intenta abrir nuevamente la misma URL del enlace en su navegador web
    Then el sistema detecta que el token del enlace ya fue consumido
    And impide el acceso al formulario de cambio de contraseña
    And muestra una pantalla informativa indicando que el enlace ya no es válido o ha expirado
    And ofrece un botón para solicitar un nuevo enlace de recuperación
```

## Puntos Abiertos
- Sin puntos abiertos pendientes en este requerimiento. Todas las definiciones funcionales se encuentran confirmadas en el PRD (RF-01.2).

## Exclusiones ("No incluye")
- Restablecimiento de contraseñas mediante llamadas telefónicas, soporte presencial en botica o códigos enviados por SMS/WhatsApp.
- Autenticación multifactor biométrica o llaves de hardware (WebAuthn) no contempladas en el MVP.
