# ADR 0014: Disponibilidad (single-node + riesgo documentado)

## Estado

Aceptado

## Contexto

El PRD RNF-03 y el KPI §8 exigen 99.5% de disponibilidad 24/7 (≈3.6 h/mes de caída permitida). El
entorno es un único servidor on-premise Windows/IIS (ADR 0002), sin presupuesto para redundancia.

## Decisión

Operar en **un solo nodo** y **documentar el riesgo** de que 99.5% es difícil de garantizar sin HA:
una falla de hardware, red o mantenimiento de Windows tumba todo. Mitigación: respaldos automáticos,
procedimiento de reinicio rápido, health checks y monitoreo, pero **no** alta disponibilidad.

## Alternativas consideradas

- **HA con 2 nodos + balanceador** — acercaría a 99.5%, pero exige duplicar servidor, replicar MySQL
  y subir la complejidad operativa fuera del alcance del MVP.

## Consecuencias

- Operación simple y de bajo costo acorde al MVP.
- Trade-off: el KPI de 99.5% queda expuesto al punto único de fallo; debe gestionarse como riesgo
  con el PM (posible renegociación del KPI o plan de HA posterior).
