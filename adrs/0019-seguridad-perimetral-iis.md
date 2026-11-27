# ADR 0019: Seguridad perimetral en IIS 10 (rate limiting, CORS, headers, WAF)

## Estado

Aceptado

## Ámbito

Transversal — seguridad perimetral de IIS para todo el sistema.

## Contexto

`AGENTS.md` §8 exige explícitamente mitigación de "SQL Injection, XSS, Bad Bots, OWASP Top 10,
DDoS" mediante las reglas de restricción de IP y módulos de seguridad de IIS. La revisión
adversarial (W-08) identificó que no existía ningún ADR ni sección del TDD que diseñara estas
medidas, lo que constituye un incumplimiento del marco de referencia del proyecto para una
plataforma pública que procesa pagos y datos de salud.

## Decisión

Activar **cinco capas de seguridad perimetral** en IIS 10, todas configurables vía `web.config`
sin software de terceros:

### 1. Dynamic IP Restrictions (rate limiting nativo de IIS)

- Limitar peticiones por IP en endpoints críticos:
  - `POST /api/v1/auth/*` (login, registro, recuperación): **3 peticiones por minuto por IP** (C-04).
  - `POST /api/v1/carrito/items` (adición al carrito): **1 req/s por IP** con ráfaga (*burst*) de hasta 5 (W-01).
  - `POST /api/v1/checkout` (inicio de checkout guest/autenticado): **3 inicios por minuto por IP** (ADR 0016).
  - `GET /api/v1/catalogo/buscar` (búsqueda): 20 req/s por IP.
- Las IPs que excedan el límite reciben HTTP 429 (Too Many Requests).
- Se habilita el módulo `DynamicIpRestrictions` de IIS con logging de IPs bloqueadas.

### 2. URL Rewrite rules contextualizadas (filtrado de patrones de ataque, W-06)

- Reglas de URL Rewrite que bloquean (HTTP 403) peticiones con patrones inequívocos de ataque:
  - SQL Injection en endpoints transaccionales: `UNION\s+SELECT`, `OR\s+1=1`, `DROP\s+TABLE`, `;\s*(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|EXEC)`.
  - **Exclusión de falsos positivos en catálogo (W-06):** El parámetro `q` en `GET /api/v1/catalogo/buscar`
    queda exento de bloqueos por caracteres ortográficos o guiones aislados (`--`, `;`), ya que las consultas
    médicas los utilizan frecuentemente y se procesan en Meilisearch sin ejecutar SQL nativo.
  - Path Traversal: `../`, `..\\`, `%2e%2e`.
  - Scanners conocidos: User-Agents de herramientas como `sqlmap`, `nikto`, `dirbuster`.
- Estas reglas son la primera línea; FastAPI/Pydantic validan y parametrizan como segunda línea.

### 3. CORS restrictivo

- Configurar CORS en FastAPI **y** en IIS `web.config` para permitir únicamente el origen del
  frontend:
  - `Access-Control-Allow-Origin: https://{dominio-frontend}` (exacto, no wildcard `*`).
  - `Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS`.
  - `Access-Control-Allow-Headers: Content-Type, Authorization`.
  - `Access-Control-Allow-Credentials: true` (para cookies de sesión si aplica).
- Peticiones desde cualquier otro origen son rechazadas por el navegador.

### 4. Headers de seguridad (HSTS, CSP, X-Content-Type-Options)

Configurar en `web.config` o en el middleware de FastAPI:

| Header | Valor | Propósito |
|--------|-------|-----------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Forzar HTTPS |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' https://js.stripe.com; frame-src 'self' https://js.stripe.com https://hooks.stripe.com; connect-src 'self' https://api.stripe.com; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'` | Mitigar XSS y habilitar pasarela Stripe (C-01) |
| `X-Content-Type-Options` | `nosniff` | Evitar MIME sniffing |
| `X-Frame-Options` | `DENY` | Evitar clickjacking |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limitar fuga de URLs |

### 5. Request Filtering (límite de payload)

- `maxAllowedContentLength`: **10 MB** (suficiente para fotos de recetas; bloquea uploads
  abusivos).
- `maxQueryString`: **4096 bytes** (bloquea query strings excesivamente largas).
- `maxUrl`: **4096 bytes**.
- Rechazar verbos HTTP no utilizados: solo `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`.

## Alternativas consideradas

- **WAF de terceros (ModSecurity para IIS)** — más completo con reglas OWASP CRS, pero añade
  complejidad de instalación y mantenimiento en un servidor on-premise con recursos limitados.
  Los módulos nativos de IIS cubren lo esencial para el MVP.
- **Solo confiar en FastAPI/Pydantic** — validan y sanitizan a nivel de aplicación, pero no
  protegen contra ataques volumétricos (DDoS) ni bloquean tráfico antes de que llegue al proceso
  Python. La defensa en profundidad requiere filtrado en la capa de servidor web.

## Consecuencias

- Cumplimiento de `AGENTS.md` §8 con módulos nativos de IIS, sin software adicional.
- Defensa en profundidad: IIS filtra a nivel de red/HTTP antes de que el tráfico llegue a FastAPI.
- Trade-off: las reglas de URL Rewrite pueden generar falsos positivos si un producto legítimo
  tiene un nombre que coincide con un patrón de ataque. Se necesita un proceso para revisar los
  logs de bloqueo y ajustar las reglas.
- La configuración de CSP debe validarse con el frontend React/Vite para no bloquear recursos
  legítimos (ej. fuentes de Google, CDN de imágenes si se usa).
