# Informe de Entrega — TESTER (HU-03)

**Unidad:** HU-03 — Catálogo y búsqueda difusa (FEATURE)
**Documento base:** `contratos/CONTRATO-HU-03.md` (v1, aprobada 2026-11-23)
**Rama:** `feat/hu-03-catalogo`
**Autor:** Agente TESTER

## 1. Entrega

Se escribieron pruebas de caja negra para la API de catálogo, el payload de lectura, la pantalla
de catálogo con scroll incremental y el contador local/temporal de `Agregar al carrito`.

La suite no verifica persistencia de carrito ni reserva de stock: la spec asigna esas responsabilidades
a HU-05.

## 2. Matriz Backend

| Caso del contrato | Prueba | Resultado |
|---|---|---|
| Typo en nombre `ibuprofno 400` | `test_typo_en_nombre_devuelve_ibuprofeno_y_payload_completo` | ROJO: endpoint 404 |
| Búsqueda por componente | `test_busqueda_por_componente_devuelve_coincidencias` | ROJO: endpoint 404 |
| `q` vacío / primera tanda | `test_q_vacio_devuelve_primera_tanda_y_cursor` | ROJO: endpoint 404 |
| Cursor incremental sin duplicados | `test_cursor_limit_carga_siguiente_tanda_sin_duplicados` | ROJO: endpoint 404 |
| Sin resultados | `test_sin_resultados_devuelve_items_vacio` | ROJO: endpoint 404 |
| Límite inválido `limit=0` | `test_limit_cero_retorna_422` | ROJO: endpoint 404 |
| `limit` ausente | `test_limit_ausente_retorna_422` | ROJO: endpoint 404 |
| Rate limit >20 consultas/IP | `test_rate_limit_mas_de_20_consultas_por_ip_retorna_429` | PASS |

La aserción `assert_catalog_payload` verifica exactamente los campos `items`, `next_cursor`,
`has_next` y todos los campos de producto fijados en la sección 4 del contrato.

## 3. Matriz Frontend

| Área | Pruebas | Resultado |
|---|---|---|
| Carga visible | `muestra carga visible mientras consulta el catálogo` | ROJO: `src/pages/Catalogo` no resuelto |
| Error visible | `muestra error visible cuando falla la consulta` | ROJO: import no resuelto |
| Estado vacío | `muestra estado visible sin resultados` | ROJO: import no resuelto |
| Búsqueda `q` | `busca usando q y GET /api/v1/catalogo/buscar` | ROJO: import no resuelto |
| Tarjeta completa | `muestra todos los campos de producto y reglas visuales exactas` | ROJO: import no resuelto |
| Scroll con `next_cursor` | `solicita la siguiente tanda con next_cursor y conserva la primera` | ROJO: import no resuelto |
| Agregar temporal | `incrementa el contador local y permanece en el catálogo` | ROJO: import no resuelto |

Las pruebas frontend esperan la pantalla observable `Catalogo` en el patrón existente `src/pages`;
no se verifican nombres internos adicionales.

## 4. Evidencia de Ejecución

### Backend

```text
7 failed, 1 passed in 3.28s
```

- Los 7 fallos funcionales reciben `404 {"detail":"Not Found"}` porque la ruta aún no está expuesta.
- El caso de rate limit pasa al observar `429` después de más de 20 consultas desde la misma IP.

### Frontend

```text
Test Files  1 failed
Tests       no tests recolectados
```

Vitest falla durante el análisis de import porque `frontend/src/pages/Catalogo` todavía no existe.

## 5. Decisiones respetadas

- Se usa cursor (`next_cursor`/`has_next`), no paginación numérica.
- Se verifica la alerta exacta de stock bajo: `Últimas unidades disponibles (menos de 6 en stock)`.
- Se verifican `Precios bajos`, descuento y `requiere_receta`.
- `Agregar al carrito` solo se verifica como contador local/temporal y permanencia en catálogo.
- No se verifica persistencia, reserva ni sincronización de carrito, porque pertenecen a HU-05.
- El rate limit usa una IP única por test, manteniendo el alcance por IP de ADR-0019.

## 6. Archivos

- `backend/tests/test_hu03_catalog.py`
- `frontend/tests/Catalogo.test.tsx`
- `informes/TESTER-HU-03.md`
