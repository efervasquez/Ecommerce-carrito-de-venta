# ADR 0009: Sesión, carrito y cache de lecturas (MySQL-only)

## Estado

Aceptado

## Ámbito

Transversal — sesión, carrito y cache de lecturas compartidos por varias historias.

## Contexto

`AGENTS.md` §3 lista "carritos y sesiones" dentro de MySQL y §9 prohíbe desperdiciar memoria en
hardware limitado. Se necesitan sesiones (guest/autenticada), persistencia del carrito y una cache
para las lecturas CQRS del catálogo (ADR 0005). La alternativa natural (Redis) añade un servicio y
consume RAM.

## Decisión

Mantener **sesión, carrito y reservas en MySQL** con un pool de conexiones optimizado (aiomysql /
SQLAlchemy async), y cachear las lecturas frecuentes del catálogo en **memoria del proceso**
bajo una política estricta de acotamiento:

### Dimensionamiento y política de cache en memoria

1. **Estructura y límite:** Cache LRU en memoria con tope estricto de **máximo 500 entradas**
   (páginas de catálogo y fichas de detalle frecuentes), limitando el consumo adicional de RAM a
   < 15 MB por proceso FastAPI.
2. **TTL (Time to Live):** Expiración temporal fija de **5 minutos (300 segundos)** para garantizar
   que precios u ofertas se refresquen automáticamente ante cambios desatendidos.
3. **Invalidación reactiva por evento:** Cada vez que el backoffice o módulo de contingencia (RF-05)
   modifica un producto, precio o stock, el servicio emite una invalidación local que purga la clave
   afectada de la cache en memoria de forma inmediata.
4. **Meilisearch como índice primario:** Las consultas de búsqueda difusa y filtrado avanzado se
   atienden directamente por Meilisearch (ADR 0006), que ya cuenta con su propio motor optimizado
   en disco/memoria, aliviando la carga sobre la cache en proceso y MySQL.

## Alternativas consideradas

- **MySQL + Redis** — sesiones más rápidas, TTL nativo distribuido y cache compartida, pero suma
  un servicio adicional a operar y consume memoria fija dedicada; descartado por la restricción de
  recursos de `AGENTS.md` §9.
- **Cache en memoria sin límite ni TTL** — riesgo de memory leak y lecturas inconsistentes tras
  actualizaciones de stock manual en contingencia.

## Consecuencias

- Un único datastore principal (MySQL), menor superficie operativa y consumo de memoria
  estrictamente acotado (< 15 MB).
- Consistencia garantizada por invalidación dirigida ante mutaciones y TTL de resguardo de 5 minutos.
- Trade-off: sin cache compartida entre procesos si IIS escala a múltiples instancias worker; cada
  instancia maneja su propio LRU local y se sincroniza por TTL y eventos del broker.
