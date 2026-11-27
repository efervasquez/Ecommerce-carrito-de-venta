# ADR 0016: Anti-abuso de carrito guest y punto de reserva (límites + reserva en checkout)

## Estado

Aceptado

## Ámbito

Historia de usuario — HU-05 (Carrito de compras, persistencia y ofertas).

## Contexto

ADR 0003 permite carritos sin autenticación ("carrito guest") para reducir fricción en el embudo de
compra. ADR 0011 reserva stock al agregar al carrito y lo libera al vencer el TTL. La combinación
crea un vector de **denegación de inventario**: un atacante puede abrir N sesiones anónimas, agregar
todo el stock a N carritos y bloquear la venta real hasta que las reservas expiren. En una botica con
stock finito de medicamentos esenciales, este ataque es trivial (un script con sesiones paralelas) y
puede vaciar el inventario visible durante horas.

La revisión adversarial (C-01) identificó que ni ADR 0011 ni ADR 0003 definían mitigaciones concretas
contra este abuso. PA-01 quedó RESUELTO (31/10/2026) fijando la reserva en 24 horas. El PM resolvió
además (decisión Opción A) diferenciar el **punto de reserva según el tipo de carrito** para acotar la
superficie de abuso sin castigar la navegación anónima. Esta decisión quedó formalizada en el PRD como
**PA-06** (reserva por tipo de sesión, RF-03.5) y **PA-07** (parámetros anti-abuso, RF-03.6).

## Decisión

### Regla central de reserva por tipo de carrito (Opción A — PA-06 / RF-03.5)

- **Cliente guest:** reserva stock **solo al llegar al checkout** (`POST /api/v1/checkout`). Mientras
  navega y llena el carrito, **no** retiene inventario.
- **Cliente autenticado:** reserva stock **al agregar al carrito** (ADR 0011).
- **Ambos casos:** TTL de **24 horas** con **liberación automática** por timeout/expiracion (PA-01),
  más la prórroga temporal de 10 minutos en checkout de ADR 0011 (C-02).

### Capas de protección sobre el carrito guest (PA-07 / RF-03.6)

1. **Límite por SKU por sesión guest:** máximo **3 unidades** del mismo producto por carrito guest.
   Si el cliente necesita más, debe autenticarse (incentiva el registro).
2. **Límite de productos distintos por carrito guest:** máximo **10 productos diferentes**.
3. **Rate limiting estricto por IP en adición al carrito (W-01):**
   - Límite perimetral en IIS y FastAPI de **1 req/s por IP con ráfaga (*burst*) de hasta 5**
     en `POST /api/v1/carrito/items`.
4. **Rate limiting por IP en inicio de checkout guest:**
   - Límite de **3 inicios de checkout por minuto por IP** en `POST /api/v1/checkout`, para impedir
     que un script abra múltiples checkouts anónimos en paralelo y reserve stock de forma masiva.
5. **Techo global de reservas guest concurrentes por IP (W-01):**
   - Una misma dirección IP o subnet no puede mantener más de **1 checkout guest activo con reservas**
     (o un tope acumulado de **máximo 15 unidades reservadas** entre todas las sesiones anónimas de esa IP).
   - Si un script intenta superar el techo, el sistema rechaza la nueva reserva y exige iniciar sesión.

Los límites son **configurables** (no hardcodeados) y pueden ajustarse por PM/BA sin redespliegue.
Los carritos de usuarios autenticados pueden tener límites más amplios o sin límite (a definir por PM/BA).

## Alternativas consideradas

- **Opción B (descartada por el PM):** mantener la reserva al agregar para todos los carritos, con TTL
  guest más corto y techos por IP más estrictos. Reducía pero no eliminaba el vector, y acortar el TTL
  guest contradecía la regla uniforme de 24h de PA-01.
- **Eliminar carrito guest (solo autenticado)** — elimina el vector por completo, pero introduce
  fricción en el embudo de compra y contradice la decisión tomada en ADR 0003.
- **CAPTCHA en adición al carrito o checkout** — efectivo contra bots, pero degrada la UX para usuarios
  legítimos.

## Consecuencias

- El vector de denegación de inventario queda prácticamente eliminado en la fase de navegación: el
  guest puede llenar el carrito sin retener una sola unidad. La superficie residual se limita a la
  ventana de checkout, acotada por rate limiting y el techo por IP.
- Un cliente legítimo guest que necesite más de 3 unidades de un medicamento o más de 10 productos
  distintos debe registrarse primero (fricción puntual que también incentiva el registro).
- Consistencia con PA-01: la regla de 24h se mantiene uniforme para ambos tipos de carrito; solo cambia
  el momento en que nace la reserva.
- Los límites deben monitorearse post-lanzamiento y ajustarse según el comportamiento real de compra.
