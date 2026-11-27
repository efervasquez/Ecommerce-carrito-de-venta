# Informe de Veredicto — HU-03 Catálogo y búsqueda difusa

**Fecha:** 2026-11-23  
**Documento base:** `contratos/CONTRATO-HU-03.md` v1, aprobado por usuario humano  
**Tipo:** Feature  
**Rama:** `feat/hu-03-catalogo`  
**Entregas:** TESTER `df771ba`, `dfe88e7`; DEV `38540ab`  
**Árbitro:** LEAD

## 1. Dictamen

🟢 **APROBADO.**

- Backend HU-03: **8/8 PASS**.
- Frontend HU-03: **7/7 PASS**.
- Suite frontend completa: **26/26 PASS**.
- Build frontend TypeScript/Vite: **exitoso**.

No quedan casos `NO VERIFICADO` ni rojos en la unidad.

## 2. Propiedad y spec

- TESTER y DEV trabajaron sobre `contratos/CONTRATO-HU-03.md` v1.
- DEV: código de backend/frontend, seed y script reproducible; commit `38540ab`.
- TESTER: pruebas; commits `df771ba` y `dfe88e7`.
- Los informes en `informes/` fueron solicitados por el LEAD.
- No se tocaron artefactos raíz no relacionados.

## 3. Matriz backend

| Caso | Prueba | Resultado |
|---|---|---|
| Typo `ibuprofno 400` | `test_typo_en_nombre_devuelve_ibuprofeno_y_payload_completo` | 🟢 PASS |
| Búsqueda por componente | `test_busqueda_por_componente_devuelve_coincidencias` | 🟢 PASS |
| `q` vacío / primera tanda | `test_q_vacio_devuelve_primera_tanda_y_cursor` | 🟢 PASS |
| Cursor sin duplicados | `test_cursor_limit_carga_siguiente_tanda_sin_duplicados` | 🟢 PASS |
| Sin resultados | `test_sin_resultados_devuelve_items_vacio` | 🟢 PASS |
| `limit=0` | `test_limit_cero_retorna_422` | 🟢 PASS |
| `limit` ausente | `test_limit_ausente_retorna_422` | 🟢 PASS |
| Rate limit 20 consultas/s/IP | `test_rate_limit_mas_de_20_consultas_por_ip_retorna_429` | 🟢 PASS |

Ejecución:

```text
8 passed in 15.72s
```

## 4. Matriz frontend

| Área | Resultado |
|---|---|
| Carga visible | 🟢 PASS |
| Error visible | 🟢 PASS |
| Estado sin resultados | 🟢 PASS |
| Búsqueda con `q` | 🟢 PASS |
| Tarjeta completa y reglas visuales | 🟢 PASS |
| Scroll incremental con cursor | 🟢 PASS |
| Contador local de `Agregar al carrito` | 🟢 PASS |

Ejecución HU-03:

```text
Test Files  1 passed (1)
Tests       7 passed (7)
```

Suite frontend completa:

```text
Test Files  8 passed (8)
Tests       26 passed (26)
```

Build:

```text
npm run build
TypeScript y Vite correctos
```

## 5. Arbitraje

Durante la primera ejecución hubo fallos de prueba, no de producción:

- El rate-limit se probaba con 21 peticiones secuenciales; el fallback local tardaba más que la ventana
  de un segundo. TESTER corrigió la prueba para usar consultas concurrentes.
- jsdom no medía el contenedor virtualizado; TESTER añadió la simulación de dimensiones y disparó el
  scroll sobre el contenedor correcto.
- La aserción de estado vacío no aceptaba `No se encontraron productos.`; TESTER alineó la aserción
  al texto observable.

Los ajustes quedaron en `dfe88e7`. No fue necesario modificar nuevamente el código DEV.

## 6. Alcance confirmado

- `Agregar al carrito` usa contador local/temporal.
- No se implementaron persistencia de carrito ni reservas de stock; pertenecen a HU-05.
- El catálogo dispone de fallback seed reproducible y configuración para Meilisearch.
