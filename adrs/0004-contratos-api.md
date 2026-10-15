# ADR 0004: Contratos de API (REST + OpenAPI + JWT/RBAC)

## Estado

Aceptado

## Contexto

El `AGENTS.md` obliga a exponer el backend mediante "APIs asíncronas", con autenticación por tokens
firmados y control estricto de roles (cada endpoint valida scopes antes de procesar). El frontend
es React. Los eventos entre módulos no son llamadas HTTP síncronas: van por el bus (ADR 0007).

## Decisión

- Exponer una API **REST JSON** versionada (`/api/v1/...`), con contrato **OpenAPI** autogenerado
  por FastAPI.
- Autenticación/autorización con **JWT firmado + scopes RBAC** por endpoint (cliente, motorizado,
  admin/farmacéutico/operador), validado en middleware antes de cada operación.
- Todo payload de petición/evento tipado y validado con **Pydantic** (y Zod en frontend).

## Alternativas consideradas

- **GraphQL** — queries flexibles para el catálogo, pero añade tooling y riesgo para un equipo
  chico y no aporta para el resto de flujos (carrito, pedidos, pagos).
- **gRPC** — alto rendimiento entre módulos, pero incompatible con React puro (exige gateway) y
  sobredimensionado para el MVP.

## Consecuencias

- Documentación de contrato gratis (Swagger/OpenAPI) y contratos validados de extremo a extremo.
- Trade-off: REST fija la forma de la respuesta por endpoint; si el frontend necesitara armar
  respuestas a medida para la lista infinita, podría requerir endpoints compuestos adicionales.
