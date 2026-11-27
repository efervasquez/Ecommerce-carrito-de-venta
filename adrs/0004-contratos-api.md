# ADR 0004: Contratos de API (REST + OpenAPI + JWT/RBAC)

## Estado

Aceptado

## Ámbito

Transversal — contratos de API, autenticación JWT/RBAC y observabilidad para todo el sistema.

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
- **Sesión Guest (S-02):** Identificada mediante cookie `HttpOnly; SameSite=Lax; Secure` firmada por
  el servidor, protegiendo carritos anónimos contra scripts maliciosos.
- **Jobs Asíncronos (W-04):** Procesos diferidos como OCR operan bajo el patrón de Job con polling
  controlado:
  - `POST /api/v1/ocr/recetas` -> `HTTP 202 Accepted` devolviendo `{ job_id, estado: "procesando", poll_interval_ms: 1500 }`.
  - `GET /api/v1/ocr/jobs/{job_id}` -> `HTTP 200` con estado (`procesando`, `completado`, `requiere_validacion`, `error`).
- **Observabilidad:** Endpoint `GET /api/v1/health` que sondea el estado de conexión a MySQL, RabbitMQ
  y Meilisearch, respondiendo `200 OK` o `503 Service Unavailable`.

## Alternativas consideradas

- **GraphQL** — queries flexibles para el catálogo, pero añade tooling y riesgo para un equipo
  chico y no aporta para el resto de flujos (carrito, pedidos, pagos).
- **gRPC** — alto rendimiento entre módulos, pero incompatible con React puro (exige gateway) y
  sobredimensionado para el MVP.

## Consecuencias

- Documentación de contrato gratis (Swagger/OpenAPI) y contratos validados de extremo a extremo.
- Trade-off: REST fija la forma de la respuesta por endpoint; si el frontend necesitara armar
  respuestas a medida para la lista infinita, podría requerir endpoints compuestos adicionales.
