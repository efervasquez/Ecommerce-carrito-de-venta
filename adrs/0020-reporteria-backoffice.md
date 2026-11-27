# ADR 0020: Reportería del Backoffice (read-model materializado en MySQL)

## Estado

Aceptado

## Ámbito

Historia de usuario — HU-11 (Reportería y métricas del Backoffice).

## Contexto

PA-05 quedó RESUELTO (31/10/2026) y formalizó en el alcance del MVP el módulo de Reportería y
Métricas del Backoffice a través de **RF-08**. El panel debe mostrar: ventas/facturación en rangos de
fecha seleccionables (RF-08.1), balance de pedidos por estado del ciclo de vida (RF-08.2) y reporte
de inventario crítico con productos de baja rotación, quiebres recurrentes y mayor rotación (RF-08.3).

ADR 0005 aplica CQRS al catálogo, pero la reportería opera sobre **pedidos, pagos y stock**, no sobre
el índice de búsqueda. Consultar en vivo las tablas transaccionales (`Pedido`, `Pago`, `Stock`)
compite con la carga operativa (250 usuarios concurrentes, RNF-01) y degrada tanto el dashboard como
el checkout. `AGENTS.md` §9 obliga a optimizar memoria/recursos en hardware limitado, descartando un
OLAP/warehouse adicional.

## Decisión

Construir la reportería como un **read-model materializado en MySQL**, separado de las tablas
transaccionales:

1. **Agregados materializados:** Tablas de resumen (ej. `reporte_ventas_diario`,
   `reporte_pedidos_estado`, `reporte_stock_critico`) pobladas por agregaciones SQL periódicas.
2. **Refresco programado:** Un **job programado (Tarea de Windows)** recalcula los agregados fuera de
   horas pico (ej. cada 15 min para inventario crítico y cada hora/cierre de día para ventas),
   siguiendo el patrón de purga de ADR 0011.
3. **Lecturas aisladas:** Los endpoints de reportería (`/api/v1/reportes/*`) leen **exclusivamente**
   las tablas materializadas, nunca las transaccionales, evitando contención con el checkout.
4. **Acceso RBAC:** Limitado a roles `admin`/`farmacéutico`/`operador` (ADR 0004), con scopes propios
   de reportería.
5. **Quiebre de stock oportuno:** El indicador de stock < 6 unidades se puede derivar del evento
   `catalogo.producto_modificado` (ADR 0006) además del refresco periódico, para alertas de
   reabastecimiento oportunas.

## Alternativas consideradas

- **Consultas en vivo sobre tablas transaccionales** — datos exactos al instante, pero genera
  contención con la carga operativa bajo 250 usuarios y queries agregadas pesadas en MySQL.
- **OLAP/warehouse separado (ClickHouse/DuckDB)** — análisis rápido y flexible, pero añade un servicio
  y consumo de memoria/CPU desproporcionado para el MVP on-premise (`AGENTS.md` §9).
- **Meilisearch para reportería** — excelente para búsqueda difusa, pero no está diseñado para
  agregaciones/group-by de ventas ni series temporales; se mantiene solo para el catálogo (ADR 0006).

## Consecuencias

- Reportería consistente y aislada, sin competir por recursos con el flujo transaccional.
- Trade-off: los agregados son **eventualmente consistentes** (retraso igual a la ventana de refresco);
  para un dashboard de gestión es aceptable y se documenta en la UI ("última actualización HH:MM").
- Un solo datastore (MySQL) y cero servicios nuevos, alineado con ADR 0009 y `AGENTS.md` §9.
