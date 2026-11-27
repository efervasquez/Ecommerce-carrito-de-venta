from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.core.broker import close_broker_connection
from src.core.database import _engine
from src.core.logging import CorrelationIdMiddleware, setup_logging
from src.core.rate_limit import AuthRateLimitMiddleware, CatalogRateLimitMiddleware
from src.modules.auth import auth_router
from src.modules.catalogo import catalogo_router
from src.modules.health import health_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("Iniciando aplicacion FastAPI - Botica la Luz", extra={"env": settings.app_env})
    try:
        yield
    finally:
        logger.info("Cerrando recursos y conexiones de la aplicacion")
        await close_broker_connection()
        if _engine is not None:
            await _engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Plataforma E-commerce - Botica la Luz API",
        description="API REST asincrona para la plataforma e-commerce de Botica la Luz.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    # Middleware de Correlation ID para observabilidad y trazabilidad (ADR-0015)
    app.add_middleware(CorrelationIdMiddleware)

    # Rate limiting perimetral de 3 req/min por IP sobre POST de auth (ADR-0019)
    app.add_middleware(AuthRateLimitMiddleware)
    app.add_middleware(CatalogRateLimitMiddleware)

    # Configuracion restrictiva de CORS (ADR-0019)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    # Normalizacion del error 422 de Pydantic a un detail de texto simple
    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        field = "requerido"
        location = "body"
        for err in exc.errors():
            loc = err.get("loc", ())
            if loc and loc[0] in {"body", "query", "path"} and len(loc) > 1:
                location = str(loc[0])
                field = str(loc[1])
                break
        if location in {"query", "path"}:
            return JSONResponse(
                status_code=422, content={"detail": f"El parámetro {field} es inválido."}
            )
        return JSONResponse(
            status_code=422, content={"detail": f"El campo {field} es requerido."}
        )

    # Registro de routers por version de API
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(catalogo_router, prefix="/api/v1")

    return app


app = create_app()
