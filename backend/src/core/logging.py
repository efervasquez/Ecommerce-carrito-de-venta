import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

CORRELATION_ID_CTX: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    return CORRELATION_ID_CTX.get()


class JSONFormatter(logging.Formatter):
    """Formateador de logs en formato JSON estructurado segun ADR-0015."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "correlation_id": getattr(record, "correlation_id", None) or get_correlation_id() or None,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class CorrelationIdFilter(logging.Filter):
    """Filtro para inyectar correlation_id en cada LogRecord emitido."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


def setup_logging(log_level: str = "INFO") -> None:
    """Configura el logger root para emitir exclusivamente JSON estructurado."""
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Limpiar handlers existentes para evitar duplicaciones
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(CorrelationIdFilter())
    root_logger.addHandler(handler)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware para extraer o generar X-Correlation-ID y propagarlo en cabeceras."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        corr_id = request.headers.get("X-Correlation-ID")
        if not corr_id:
            corr_id = str(uuid.uuid4())

        token = CORRELATION_ID_CTX.set(corr_id)
        request.state.correlation_id = corr_id

        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = corr_id
            return response
        finally:
            CORRELATION_ID_CTX.reset(token)
