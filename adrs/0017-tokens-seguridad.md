# ADR 0017: Tokens de seguridad (activación + recuperación de contraseña)

## Estado

Aceptado

## Ámbito

Historia de usuario — HU-01 (Autoregistro) y HU-02 (Recuperación de contraseña).

## Contexto

El PRD RF-01 define autoregistro con envío de contraseña provisional y recuperación de contraseña
con link de un solo uso. La revisión adversarial (C-03) identificó que no existía ningún ADR ni
sección que diseñara la generación, firma, expiración ni el mecanismo de un solo uso de estos
tokens. Sin este diseño, el implementador puede producir tokens predecibles, reutilizables o sin
expiración, lo que en una plataforma con datos de salud (LPDP) equivale a account takeover.

Además, se decidió (con el PM) **reemplazar el envío de contraseña provisional en texto plano**
por un **link de activación** donde el usuario crea su propia contraseña. Esto elimina el riesgo
de contraseñas en tránsito y alinea con buenas prácticas de seguridad. **El PRD debe actualizarse
para reflejar este cambio en RF-01.1.**

## Decisión

### Mecanismo de token

Usar **tokens opacos** (UUID v4 generado con CSPRNG) almacenados en una tabla MySQL `tokens`:

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | BIGINT PK | Auto-incremental |
| `token_hash` | VARCHAR(64) | SHA-256 del token (nunca se almacena el token en claro) |
| `tipo` | ENUM('activacion', 'recuperacion') | Propósito del token |
| `usuario_id` | BIGINT FK → Usuario | Usuario al que pertenece |
| `expira_en` | DATETIME | Timestamp de expiración |
| `usado_en` | DATETIME NULL | NULL si no se ha usado; timestamp del uso |
| `creado_en` | DATETIME | Timestamp de creación |

### Flujo de activación (autoregistro)

1. El usuario envía su email a `POST /api/v1/auth/registro`.
2. El backend crea el `Usuario` con estado `pendiente_activacion` y genera un token UUID v4.
3. Se almacena el `SHA-256(token)` en la tabla `tokens` con `tipo = 'activacion'` y
   `expira_en = NOW() + 24 horas`.
4. Se publica un evento al bus (RabbitMQ) para que el worker de correo envíe el link:
   `https://{dominio}/activar?token={token_crudo}`.
5. Al hacer clic, el frontend envía `POST /api/v1/auth/activar` con el token.
6. El backend calcula `SHA-256(token_recibido)`, busca en `tokens` donde
   `token_hash = hash AND tipo = 'activacion' AND usado_en IS NULL AND expira_en > NOW()`.
7. Si existe: marca `usado_en = NOW()`, cambia el estado del usuario a `activo`, y presenta el
   formulario de creación de contraseña.
8. Si no existe o ya se usó: responde con error genérico (no revela si el token existió).

### Flujo de recuperación de contraseña

Idéntico al flujo de activación, con `tipo = 'recuperacion'` y `expira_en = NOW() + 1 hora`
(ventana más corta por ser más sensible). Al validar, se presenta el formulario de nueva
contraseña.

### Protección contra enumeración de usuarios y agotamiento de cuota (C-04)

- Tanto `POST /api/v1/auth/registro` como `POST /api/v1/auth/recuperar` responden siempre con
  el mismo HTTP 200 y el mismo cuerpo (`"Si el email existe, recibirás un correo"`) **sin importar
  si el email está registrado o no**.
- El tiempo de respuesta debe ser constante (usar `asyncio.sleep` de relleno si la rama "no
  existe" es más rápida) para evitar timing attacks.
- **Throttling y Cooldown por Email (C-04):** Para impedir ataques de denegación de servicio que
  agoten la cuota diaria del proveedor de correo (Brevo/SendGrid):
  - Se impone un **cooldown de 15 minutos por dirección de correo**: si ya se despachó un token
    hacia ese email hace menos de 15 minutos, el backend responde con el mismo HTTP 200 pero **no
    encola ningún nuevo mensaje en RabbitMQ ni consume la cuota del proveedor**.
  - Se fija un **tope máximo de 3 solicitudes de recuperación al día por cuenta**.
  - Al generar un nuevo token de recuperación, cualquier token previo no utilizado de ese usuario
    se invalida de inmediato (`usado_en = NOW()`).

### Purga de tokens

Los tokens expirados o usados se purgan con una Tarea programada de Windows (misma estrategia que
la purga de carritos, ADR 0011) cada 6 horas.

## Alternativas consideradas

- **JWT firmado con `exp`** — stateless para la validación de expiración, pero "un solo uso"
  requiere igualmente una tabla en DB para invalidar el token después del uso. No aporta ventaja
  real sobre el token opaco y añade complejidad (firma, rotación de clave de JWT, tamaño del
  token en la URL).
- **Mantener contraseña provisional por email (como el PRD literal)** — más simple de
  implementar, pero envía credenciales en texto plano por un canal no cifrado (email), deja la
  contraseña en el buzón indefinidamente, y el usuario puede nunca cambiarla. Riesgo LPDP
  inaceptable.

## Consecuencias

- Tokens seguros, de un solo uso, con expiración y almacenamiento hasheado. Resistentes a
  enumeración de usuarios y timing attacks.
- Trade-off: requiere actualizar RF-01.1 del PRD para reflejar el cambio de contraseña provisional
  a link de activación. El flujo de registro tiene un paso más (clic en email → crear contraseña)
  que la contraseña provisional directa.
- Se necesita la tabla `tokens` en el modelo de datos (amplía ADR 0003).
