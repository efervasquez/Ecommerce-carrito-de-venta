from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.core.broker import close_broker_connection
from src.core.database import _engine
from src.core.logging import CorrelationIdMiddleware, setup_logging
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

    # Configuracion restrictiva de CORS (ADR-0019)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    # Registro de routers por version de API
    app.include_router(health_router, prefix="/api/v1")

    return app


app = create_app()
