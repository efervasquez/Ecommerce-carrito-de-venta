# Priorización y orden de ejecución de HUs — Botica la Luz

**Fecha:** 31/10/2026
**Decide:** Usuario humano / Product Owner
**Estado:** Aprobado
**Contexto:** Todas las HUs (01–11) están definidas y sin puntos abiertos (PRD v1.8). Este documento fija el orden de ejecución y la clasificación MoSCoW para DEV / TESTER / LEAD.

---

## 1. Decisiones aplicadas

1. **HU-10 (Contingencia) queda como contingencia pura.** El catálogo inicial se carga vía seed/scripts (AGENTS.md), por lo que HU-10 **no** sube a P0 y se programa como mecanismo de resiliencia ante caídas del ERP (P2).
2. **HU-06 (OCR) se adelanta a P1**, aceptando el riesgo técnico (precisión del OCR, procesamiento en worker).

---

## 2. Orden de ejecución

| # | HU | Título | Tier | Depende de | Justificación |
|---|---|---|---|---|---|
| 1 | HU-01 | Autoregistro y autenticación de clientes | 🔴 P0 | — | Base de identidad, sesión y RBAC. Todo (carrito, pago, backoffice) cuelga de la sesión. Ya tiene contrato aprobado. |
| 2 | HU-02 | Recuperación de contraseña | 🟢 P1 | HU-01 | Completa el módulo de usuarios; barato y obligatorio para un go-live real. |
| 3 | HU-03 | Catálogo scroll infinito + Fuzzy Search | 🔴 P0 | — | Valor visible central; habilita la búsqueda y consulta de stock. |
| 4 | HU-04 | Vista de detalle extendida del producto | 🟢 P1 | HU-03 | Decisión de compra informada (flag de receta, contraindicaciones). |
| 5 | HU-05 | Carrito + persistencia + reserva 24h + ofertas | 🔴 P0 | HU-03 | Corazón transaccional; habilita HU-06 (OCR) y HU-07 (pago). |
| 6 | HU-07 | Pasarela de pagos Stripe Sandbox | 🔴 P0 | HU-05 | Convierte el carrito en ingreso; crea el pedido en estado `Registrado`. |
| 7 | HU-06 | Automatización OCR de recetas médicas | 🟢 P1 | HU-05 | Diferenciador de alto valor; riesgo técnico aceptado (decisión humana). |
| 8 | HU-08 | Buzón de despacho y ciclo de vida | 🟡 P2 | HU-07 | Cumplimiento operativo de los pedidos confirmados. |
| 9 | HU-10 | Contingencia y edición manual de stock | 🟡 P2 | HU-03 | Resiliencia ante caídas del ERP; contingencia pura (catálogo se carga por seed). |
| 10 | HU-09 | Reclamos y logística inversa | 🟢 P3 | HU-08 | Flujo de borde post-entrega; no bloquea lanzar la venta. |
| 11 | HU-11 | Reportería y métricas del Backoffice | 🟢 P3 | HU-07, HU-08 | Operación madura; requiere datos reales de ventas y pedidos. |

---

## 3. Camino crítico mínimo para vender (MVP)

`HU-01 → HU-03 → HU-04 → HU-05 → HU-07 → HU-08`

---

## 4. Notas

- Los identificadores `HU-XX` son **estables** y **no se renombran**, para no romper las referencias existentes en `PRD.md`, `SPRINT0.md`, `adrs/` y `contratos/`. El orden de ejecución se expresa aquí, no en el nombre de archivo.
- Tiers: **P0** crítico · **P1** alto · **P2** medio · **P3** posterior.

---

## 5. Clasificación MoSCoW (aprobada)

**Fecha:** 01/11/2026 · **Decide:** Product Owner · **Estado:** Aprobado

| Categoría | HUs | Justificación |
|---|---|---|
| **Must have** | HU-01, HU-03, HU-04, HU-05, HU-07, HU-08 | Camino crítico: sin esto no se vende ni se entrega. Identidad, catálogo, detalle (flag de receta), carrito, pago y despacho. |
| **Should have** | HU-02, HU-06 | Importantes, no bloquean el lanzamiento. Recuperación de contraseña y OCR de recetas (riesgo asumido). |
| **Could have** | HU-10, HU-11 | Deseables, se recortan primero. Contingencia manual de stock (catálogo por seed) y reportería Backoffice. |
| **Won't have (este release)** | HU-09 | Reclamos y logística inversa: post-venta/borde; se difiere a release posterior. |

Orden de ejecución MoSCoW:

```text
MUST     HU-01 → HU-03 → HU-04 → HU-05 → HU-07 → HU-08
SHOULD   HU-02, HU-06
COULD    HU-10, HU-11
WON'T    HU-09
```
