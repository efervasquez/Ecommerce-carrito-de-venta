# HU-03: Registro obligatorio e inicio de sesión del cliente

## Historia de usuario
Como Cliente de la farmacia  
Quiero registrarme con mis datos personales y seleccionar mi canal principal de notificación, e iniciar sesión en la PWA  
Para poder armar pedidos, realizar compras y recibir notificaciones sobre el estado de mis solicitudes  

## Alcance específico de la HU
- **Sección del PRD:** 3. Alcance — Incluye (Cliente: Registro e inicio de sesión obligatorio, Datos de registro, Canal principal de notificación), 3. Aplicativo (Roles diferenciados), 5. No incluye (*Autenticación multifactor*), 7. Consideraciones regulatorias y datos sensibles.
- **Criterios de éxito asociados:** Criterio 1 (*Un cliente registrado puede generar un pedido completo desde la PWA*).
- **Cobertura:** Formulario de registro con captura de documento, nombre, dirección completa (país, departamento, distrito y calle), teléfono, correo electrónico y selección de un único canal principal de notificación (SMS, WhatsApp o Correo). Inicio de sesión y autenticación básica en la PWA.

## Criterios de aceptación funcionales
1. **Obligatoriedad de autenticación:** El cliente debe estar registrado e iniciar sesión obligatoriamente para poder generar un pedido.
2. **Campos obligatorios de registro:** El formulario de registro debe exigir sin excepción:
   - Documento de identidad.
   - Nombre completo.
   - Dirección compuesta: País, Departamento, Distrito y Calle/Número.
   - Teléfono de contacto.
   - Correo electrónico.
   - Selección de un único canal principal de notificación entre: `Mensaje de texto (SMS)`, `WhatsApp` o `Correo electrónico`.
3. **Unicidad de cuenta:** No se permite más de una cuenta registrada con el mismo documento de identidad o correo electrónico.
4. **Almacenamiento seguro:** Las contraseñas deben cifrarse y los datos personales deben tratarse como datos sensibles bajo las consideraciones de la Sección 7 del PRD.
5. **Sesión en PWA:** Una vez autenticado, la sesión del cliente debe mantenerse activa en el navegador de la PWA según estándares web usuales.

## Escenarios Gherkin

### Escenario 1 — Camino feliz: Registro exitoso con todos los campos requeridos
```gherkin
Feature: Registro e inicio de sesión de cliente
  Scenario: Cliente nuevo completa su registro satisfactoriamente
    Given que el cliente ingresa a la PWA y no cuenta con una sesión iniciada
    When completa el formulario de registro con su documento "12345678", nombre "Juan Pérez", dirección (País: "Perú", Departamento: "Lima", Distrito: "Miraflores", Calle: "Av. Larco 123"), teléfono "999888777", correo "juan@example.com", contraseña segura y selecciona como canal principal "WhatsApp"
    And presiona "Registrarse"
    Then el sistema crea la cuenta del cliente exitosamente
    And le permite iniciar sesión en la PWA con sus credenciales recién creadas
```

### Escenario 2 — Caso borde: Intento de registro con omisión del canal principal de notificación
```gherkin
Feature: Registro e inicio de sesión de cliente
  Scenario: Cliente intenta registrarse sin seleccionar su canal principal de notificación
    Given que el cliente está en el formulario de registro
    When completa su documento, nombre, dirección, teléfono y correo pero no selecciona ningún canal de notificación
    And intenta confirmar el registro
    Then el sistema no crea la cuenta
    And resalta el campo de selección de canal principal indicando que es obligatorio elegir entre SMS, WhatsApp o Correo electrónico
```

## Puntos Abiertos
- Sin puntos abiertos pendientes. Todas las definiciones fueron confirmadas en el PRD.

## Exclusiones ("No incluye")
- Pasarela de pago en línea (fuera de alcance en Sección 5 del PRD).
- Autenticación multifactor (MFA/2FA) por SMS o token (excluido explícitamente en Sección 5).
- Inicio de sesión con redes sociales (OAuth con Google, Facebook o Apple).
- Notificaciones multicanal simultáneas (el cliente debe elegir un único canal principal).
