# ADR 0016: Anti-abuso de carrito guest (límites de reserva + rate limiting)

## Estado

Aceptado

## Contexto

ADR 0003 permite carritos sin autenticación ("carrito guest") para reducir fricción en el embudo
de compra. ADR 0011 reserva stock al agregar al carrito y lo libera solo al vencer el TTL. La
combinación crea un vector de **denegación de inventario**: un atacante puede abrir N sesiones
anónimas, agregar todo el stock a N carritos y bloquear la venta real hasta que las reservas
expiren. En una botica con stock finito de medicamentos esenciales, este ataque es trivial (un
script con sesiones paralelas) y puede vaciar el inventario visible durante horas, contradice el
KPI de "25% de facturación por canal web" y la misión de atención 24/7.

La revisión adversarial (C-01) identificó que ni ADR 0011 ni ADR 0003 definen mitigaciones
concretas contra este abuso, a pesar de que ADR 0003 reconoce la superficie de ataque en su
sección de consecuencias.

## Decisión

Imponer **tres capas de protección** sobre el carrito guest:

1. **Límite por SKU por sesión guest:** máximo **3 unidades** del mismo producto por carrito guest.
   Si el cliente necesita más, debe autenticarse (incentiva el registro).
2. **Límite de productos distintos por carrito guest:** máximo **10 productos diferentes**. Supera
   la compra razonable de una visita de farmacia; si necesita más, debe autenticarse.
3. **Rate limiting estricto por IP en adición al carrito (W-01):**
   - Límite perimetral en IIS y FastAPI de **1 req/s por IP con ráfaga (*burst*) de hasta 5**
     en `POST /api/v1/carrito/items`.
4. **Techo global de reservas anónimas concurrentes por IP (W-01):**
   - Una misma dirección IP o subnet no puede mantener más de **1 carrito guest activo con reservas**
     (o un tope acumulado de **máximo 15 unidades reservadas** entre todas las sesiones anónimas de esa IP).
   - Si un script intenta abrir múltiples sesiones anónimas en paralelo para eludir el límite de 3 unidades,
     el sistema rechaza la nueva reserva y le exige iniciar sesión para continuar.

Los límites son **configurables** (no hardcodeados) y pueden ajustarse por PM/BA sin redespliegue.
Los carritos de usuarios autenticados pueden tener límites más amplios o sin límite (a definir
por PM/BA).

## Alternativas consideradas

- **Solo rate limiting sin límites de cantidad** — reduce la velocidad del ataque pero no lo
  impide: un atacante paciente con múltiples IPs puede igualmente agotar el stock.
- **Eliminar carrito guest (solo autenticado)** — elimina el vector por completo, pero introduce
  fricción en el embudo de compra y contradice la decisión tomada en ADR 0003.
- **CAPTCHA en adición al carrito** — efectivo contra bots, pero degrada la UX para usuarios
  legítimos en cada adición de producto.

## Consecuencias

- El vector de denegación de inventario queda acotado: un atacante puede reservar como máximo
  3 × 10 = 30 unidades por sesión, limitado además por rate limiting.
- Trade-off: un cliente legítimo guest que necesite más de 3 unidades de un medicamento o más de
  10 productos distintos debe registrarse primero. Esto puede generar fricción puntual, pero
  también es un incentivo natural al registro.
- Los límites deben monitorearse post-lanzamiento y ajustarse según el comportamiento real de
  compra de la botica.
