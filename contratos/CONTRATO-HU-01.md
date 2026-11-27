# CONTRATO — HU-01 Autoregistro rápido y autenticación de clientes

**Versión:** v1  
**Estado:** Aprobado (2026-10-16, usuario humano)  
**HU:** [HU-01-autoregistro-y-autenticacion-cliente.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/HUs/HU-01-autoregistro-y-autenticacion-cliente.md)  

---

## 1. Paquete de contexto

| Fuente | Por qué entra |
|---|---|
| [HU-01](file:///C:/Temp2/Ecommerce-carrito-de-venta/HUs/HU-01-autoregistro-y-autenticacion-cliente.md) | Historia base, formulario de un solo campo, criterios funcionales y escenarios Gherkin. |
| [TECH-DESIGN.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md) §Autoregistro | Reglas técnicas: link de activación en vez de password provisional, anti-enumeración, timing constante y cooldown de 15 min. |
| [ADR-0001](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0001-componentes.md) | Monolito modular FastAPI por capas y separación operativa con workers. |
| [ADR-0003](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0003-modelo-datos.md) | Entidades `Usuario` (rol `cliente`, estados `pendiente_activacion`, `activo`) y `Token`. |
| [ADR-0004](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0004-contratos-api.md) | Convención REST JSON `/api/v1/auth/*`, validación con Pydantic, autenticación JWT con claims RBAC. |
| [ADR-0007](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0007-broker-workers.md) | Publicación de eventos de correo en cola segmentada `email.auth` hacia RabbitMQ. |
| [ADR-0010](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0010-estado-frontend.md) | Gestión de sesión de cliente en frontend mediante Zustand. |
| [ADR-0015](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0015-lpdp.md) | Minimización de PII, prohibición estricta de loguear tokens o contraseñas en claro. |
| [ADR-0017](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0017-tokens-seguridad.md) | Reemplazo de contraseña provisional por link de activación, token opaco UUID v4 con hash SHA-256 en DB, expiración de 24 horas y cooldown anti-spam. |
| [ADR-0018](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0018-transporte-smtp.md) | Formato del link transaccional despachado vía relay de correo (`https://{dominio}/activar?token={token_crudo}`). |
| [ADR-0019](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0019-seguridad-perimetral-iis.md) | Rate limiting perimetral de máximo 3 peticiones por minuto por IP en endpoints de auth. |

---

## 2. Interfaz observable

La funcionalidad se expone y verifica mediante tres interfaces observables:
1. **API REST HTTP (`/api/v1/auth/*`)**: Endpoints síncronos consumidos por el frontend y testeables vía HTTP.
2. **Interfaz Web de Usuario (SPA React)**: Pantallas accesibles en rutas `/registro`, `/activar` y `/login`.
3. **Bus de Eventos RabbitMQ**: Mensajes publicados en la cola `email.auth`.

---

## 3. Comportamiento Observable

### 3.1. Solicitud de Autoregistro

**Entrada HTTP:**
```http
POST /api/v1/auth/registro
Content-Type: application/json

{
  "email": "cliente.nuevo@ejemplo.com"
}
```

**Casos:**

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| **Camino feliz:** Usuario nuevo con email válido | Email válido no registrado previamente | HTTP 200 `{"message": "Si el correo ingresado es válido, recibirás un enlace de activación en tu buzón."}`.<br>Crea `Usuario` con `estado = 'pendiente_activacion'`, genera token opaco UUID v4 guardando `token_hash = SHA256(token)`, y publica evento en cola RabbitMQ `email.auth`. | HU-01 Criterio 1 y 2 + ADR-0017 + TECH-DESIGN.md |
| **Email duplicado o ya existente** | Email ya registrado en DB (activo o pendiente) | HTTP 200 con **exactamente el mismo JSON** y mismo tiempo de respuesta que el camino feliz.<br>Efecto interno: NO crea usuario duplicado, NO publica evento de activación si hay cooldown activo. | ADR-0017 §Protección contra enumeración |
| **Cooldown activo (< 15 min)** | Email que ya solicitó registro hace menos de 15 minutos | HTTP 200 con **exactamente el mismo JSON**.<br>Efecto interno: No se publica mensaje en RabbitMQ para preservar cuota SMTP. | ADR-0017 §Throttling y Cooldown |
| **Error: Formato de email inválido** | Cadena sin `@`, sin dominio o con caracteres inválidos (ej. `"correo_sin_dominio.com"`) | HTTP 422 Unprocessable Entity `{"detail": "Formato de correo electrónico inválido"}`.<br>No se crea usuario ni se encolan eventos. | HU-01 Escenario 2 |
| **Error: Payload vacío o campo ausente** | `{}` o `{"email": ""}` | HTTP 422 Unprocessable Entity.<br>Indica campo requerido. | ADR-0004 (Validación Pydantic) |
| **Error: Rate limit excedido por IP** | Más de 3 peticiones por minuto desde la misma IP | HTTP 429 Too Many Requests `{"detail": "Demasiadas solicitudes. Por favor, intente nuevamente en unos minutos."}`. | ADR-0019 §Dynamic IP Restrictions |

---

### 3.2. Activación de Cuenta y Creación de Contraseña

**Entrada HTTP:**
```http
POST /api/v1/auth/activar
Content-Type: application/json

{
  "token": "a4f8d3b2-7c91-4e20-91a5-8c2910fa9821",
  "password": "Password123!"
}
```

**Casos:**

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| **Camino feliz:** Token válido y contraseña segura | Token UUID existente en `tokens` con `tipo = 'activacion'`, `usado_en IS NULL`, `expira_en > NOW()`, y contraseña que cumple requisitos de complejidad | HTTP 200 `{"message": "Cuenta activada exitosamente. Ya puedes iniciar sesión."}`.<br>Efecto: Actualiza `tokens.usado_en = NOW()`, pasa usuario a `estado = 'activo'`, persiste `password_hash` con bcrypt/argon2. Invalida tokens previos. | ADR-0017 §Flujo de activación |
| **Error: Token ya usado** | Token UUID cuyo registro tiene `usado_en IS NOT NULL` | HTTP 400 Bad Request `{"detail": "El enlace de activación es inválido o ha expirado."}`.<br>No altera el estado del usuario. | ADR-0017 §Flujo de activación |
| **Error: Token expirado (> 24 horas)** | Token UUID cuya fecha `expira_en <= NOW()` | HTTP 400 Bad Request `{"detail": "El enlace de activación es inválido o ha expirado."}`. | ADR-0017 §Flujo de activación |
| **Error: Token inexistente o alterado** | Token que no existe en DB o formato no UUID | HTTP 400 Bad Request `{"detail": "El enlace de activación es inválido o ha expirado."}`. Mensaje idéntico para evitar enumeración de tokens. | ADR-0017 §Flujo de activación |
| **Error: Contraseña débil** | Menos de 8 caracteres o sin cumplir complejidad (al menos 1 mayúscula, 1 minúscula y 1 número) | HTTP 422 Unprocessable Entity `{"detail": "La contraseña debe tener al menos 8 caracteres e incluir mayúsculas, minúsculas y números."}`.<br>El token no se marca como usado. | Decisión humana aprobada (DP-2) |

---

### 3.3. Autenticación / Inicio de Sesión (Login)

**Entrada HTTP:**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "cliente.nuevo@ejemplo.com",
  "password": "Password123!"
}
```

**Casos:**

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| **Camino feliz:** Credenciales válidas de usuario activo | Email registrado y contraseña coincidente con hash, usuario con `estado = 'activo'` | HTTP 200 OK con payload:<br>`{"access_token": "<jwt_string>", "token_type": "bearer", "expires_in": 3600, "usuario": {"id": 1, "email": "cliente.nuevo@ejemplo.com", "rol": "cliente"}}`.<br>Token firmado con secret seguro, **expiración de 1 hora (3600 segundos)**, claims `sub`, `rol` y `scopes = ["cliente"]`. | HU-01 Criterio 4 + ADR-0004 + Decisión humana aprobada (DP-3) |
| **Error: Contraseña incorrecta** | Email registrado pero contraseña errónea | HTTP 401 Unauthorized `{"detail": "Credenciales inválidas o cuenta no activada."}`. | ADR-0004 / Seguridad estándar |
| **Error: Cuenta no activada** | Email registrado pero con `estado = 'pendiente_activacion'` | HTTP 401 Unauthorized con **el mismo mensaje**: `{"detail": "Credenciales inválidas o cuenta no activada."}` (no revela si la contraseña fue correcta). | ADR-0004 / Anti-enumeración |
| **Error: Cuenta suspendida** | Usuario con `estado = 'suspendido'` | HTTP 403 Forbidden `{"detail": "Cuenta suspendida. Por favor, contacte a soporte."}`. | ADR-0003 (Estados de usuario) |
| **Error: Email inexistente** | Email que no existe en el sistema | HTTP 401 Unauthorized `{"detail": "Credenciales inválidas o cuenta no activada."}`. | ADR-0004 / Anti-enumeración |

---

### 3.4. Inspección de Sesión Activa

**Entrada HTTP:**
```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

**Casos:**

| Caso | Entrada | Salida esperada | Origen |
|---|---|---|---|
| **Camino feliz:** Token válido | Cabecera `Authorization` con JWT válido emitido por el sistema | HTTP 200 OK con payload:<br>`{"id": 1, "email": "cliente.nuevo@ejemplo.com", "rol": "cliente", "estado": "activo"}` | HU-01 Criterio 4 + ADR-0004 |
| **Error: Token ausente o malformado** | Petición sin header o con token corrupto | HTTP 401 Unauthorized `{"detail": "No autenticado o token inválido."}` | ADR-0004 |
| **Error: Token expirado (> 1 hora)** | JWT con timestamp `exp` vencido | HTTP 401 Unauthorized `{"detail": "Token expirado. Inicie sesión nuevamente."}` | ADR-0004 + Decisión humana (DP-3) |

---

### 3.5. Interfaz de Usuario Frontend (Web App)

| Pantalla | Ruta | Elementos observables mínimos | Comportamiento | Origen |
|---|---|---|---|---|
| **Registro** | `/registro` | Input con id/name `email`, botón visible con texto exacto `"Registrarme"`. | Al hacer submit exitoso, renderiza en pantalla el texto exacto: `"Si el correo ingresado es válido, recibirás un enlace de activación en tu buzón."`. En caso de email inválido, muestra error visual en el campo sin enviar la petición. | HU-01 Escenario 1 y 2 |
| **Activación** | `/activar?token=<token>` | Inputs `password`, `confirm_password`, botón con texto `"Activar cuenta"`. | Extrae el query param `token`. Al completar exitosamente, muestra mensaje `"Cuenta activada exitosamente"` y redirige o enlaza a `/login`. Si el token es inválido, muestra `"El enlace de activación es inválido o ha expirado"`. | ADR-0017 §Flujo de activación |
| **Login** | `/login` | Inputs `email`, `password`, botón con texto `"Iniciar sesión"`. | Al recibir 200, almacena sesión en Zustand y redirige a la vista principal (`/`). Si recibe 401, muestra mensaje de error en pantalla. | HU-01 Criterio 4 + ADR-0010 |

---

### 3.6. Evento de Correo en RabbitMQ

* **Cola:** `email.auth`
* **Formato del payload JSON publicado:**
```json
{
  "evento": "auth.activacion_solicitada",
  "correlation_id": "c1f8d3b2-7c91-4e20-91a5-8c2910fa9800",
  "timestamp": "2026-10-16T12:00:00Z",
  "payload": {
    "email": "cliente.nuevo@ejemplo.com",
    "token": "a4f8d3b2-7c91-4e20-91a5-8c2910fa9821",
    "url_activacion": "https://localhost:5173/activar?token=a4f8d3b2-7c91-4e20-91a5-8c2910fa9821",
    "expira_en": "2026-10-17T12:00:00Z"
  }
}
```
* **Origen:** ADR-0007 §Segmentación de Colas (`email.auth`) + ADR-0018 §Tipos de correo.

---

## 4. Nombres que no se negocian (Contrato estricto)

| Tipo | Valor exacto | Contexto |
|---|---|---|
| **Ruta API** | `POST /api/v1/auth/registro` | Endpoint de solicitud de autoregistro |
| **Ruta API** | `POST /api/v1/auth/activar` | Endpoint de activación de cuenta con token |
| **Ruta API** | `POST /api/v1/auth/login` | Endpoint de inicio de sesión con email y password |
| **Ruta API** | `GET /api/v1/auth/me` | Endpoint de perfil y verificación de sesión activa |
| **Ruta Frontend** | `/registro` | Página web de registro rápido |
| **Ruta Frontend** | `/activar` | Página web de creación de contraseña tras clic en link de email |
| **Ruta Frontend** | `/login` | Página web de acceso a la cuenta |
| **Cola RabbitMQ** | `email.auth` | Cola de mensajería para eventos de autenticación |
| **Nombre de Evento** | `auth.activacion_solicitada` | Tipo de evento emitido al bus |
| **Campo payload** | `email` | Correo electrónico en peticiones |
| **Campo payload** | `token` | Token UUID v4 en activación |
| **Campo payload** | `password` | Contraseña en activación y login |
| **Campo payload** | `access_token` | Token JWT en respuesta de login |
| **Campo payload** | `expires_in` | Duración en segundos del JWT (`3600`) |
| **Mensaje visible** | `"Si el correo ingresado es válido, recibirás un enlace de activación en tu buzón."` | Respuesta ante registro (éxito o anti-enumeración) |
| **Mensaje visible** | `"Cuenta activada exitosamente. Ya puedes iniciar sesión."` | Respuesta ante activación válida |
| **Mensaje visible** | `"El enlace de activación es inválido o ha expirado."` | Respuesta ante token inválido/expirado |
| **Mensaje visible** | `"Credenciales inválidas o cuenta no activada."` | Respuesta ante login fallido |
| **Texto de botón** | `"Registrarme"` | Botón del formulario en `/registro` |
| **Texto de botón** | `"Activar cuenta"` | Botón del formulario en `/activar` |
| **Texto de botón** | `"Iniciar sesión"` | Botón del formulario en `/login` |

---

## 5. Decisiones propuestas y resoluciones

| # | Decisión | Por qué hace falta | Estado |
|---|---|---|---|
| **DP-1** | Reemplazo definitivo de "contraseña provisional en claro" por "enlace de activación de cuenta con token de un solo uso" donde el cliente crea su clave. | La HU-01 original mencionaba "contraseña provisional", pero [ADR-0017](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0017-tokens-seguridad.md) y [TECH-DESIGN.md](file:///C:/Temp2/Ecommerce-carrito-de-venta/TECH-DESIGN.md) §Autoregistro decidieron eliminar contraseñas en texto plano por correo para cumplir LPDP. | **Aprobada** por el usuario humano (2026-10-16). |
| **DP-2** | Política mínima de complejidad de contraseña: al menos 8 caracteres, al menos una letra mayúscula, una letra minúscula y un número. | La HU no fijaba reglas de complejidad para la contraseña creada por el usuario; previene contraseñas débiles. | **Aprobada** por el usuario humano (2026-10-16). |
| **DP-3** | Tiempo de vida del JWT de acceso (`access_token`): **1 hora (3600 segundos)**. | Define el TTL del token JWT para expiración segura de la sesión. | **Aprobada** con valor de 1 hora por el usuario humano (2026-10-16). |
| **DP-4** | Anti-enumeración estricta con HTTP 200 y mensaje genérico idéntico tanto para emails nuevos como ya registrados. | Protege la privacidad de los clientes impidiendo que un atacante descubra qué correos están registrados. | **Aprobada** por el usuario humano (2026-10-16). |

---

## 6. Fuera del contrato (libertad del DEV)

- Algoritmo interno de hash para passwords (bcrypt o argon2id con parámetros estándar).
- Nombres de funciones internas, métodos de servicio y repositorios (respetando arquitectura por capas `Route -> Controller -> Service -> Repository`).
- Configuración interna del worker de envío SMTP (librería de cliente HTTP hacia Brevo/SendGrid).
- Estilos visuales exactos (CSS/Tailwind) del formulario, siempre que se respeten los IDs/nombres de inputs, textos de botones y mensajes visibles fijados en la sección 4.

---

## 7. Preguntas abiertas y Resoluciones

1. **Ratificación de Enlace de Activación vs. Contraseña Provisional:** Resuelto: Se implementa el flujo de Enlace de Activación con token de un solo uso ([ADR-0017](file:///C:/Temp2/Ecommerce-carrito-de-venta/adrs/0017-tokens-seguridad.md)).
2. **Requisitos de contraseña (DP-2):** Resuelto: Aprobada regla de contraseña: mínimo 8 caracteres, al menos 1 mayúscula, 1 minúscula y 1 número.
3. **Expiración del JWT (DP-3):** Resuelto: Vigencia de 1 hora (3600 s) para el token de sesión JWT del cliente.

---

## 8. Changelog

| Versión | Fecha | Cambio | Motivo | Aprobado por |
|---|---|---|---|---|
| v1 | 2026-10-16 | Aprobación inicial del contrato con vigencia de JWT fijada en 1 hora y flujo de activación con token seguro. | Ratificación de DP-1, DP-2, DP-3 (1 hora) y DP-4. | Usuario humano |
