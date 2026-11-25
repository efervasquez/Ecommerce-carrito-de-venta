import threading
import time
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.config import get_settings

RATE_LIMIT_DETAIL = "Demasiadas solicitudes. Por favor, intente nuevamente en unos minutos."

AUTH_POST_PATHS = {
    "/api/v1/auth/registro",
    "/api/v1/auth/activar",
    "/api/v1/auth/login",
    "/api/v1/auth/recuperar",
    "/api/v1/auth/restablecer",
}

CATALOG_GET_PATH = "/api/v1/catalogo/buscar"
CART_ADD_PATH = "/api/v1/carrito/items"
CHECKOUT_PATH = "/api/v1/checkout"


class RateLimiter:
    """Limitador de peticiones por clave (IP) con ventana fija en memoria.

    Segunda linea de defensa (ADR-0019): la primera es Dynamic IP Restrictions
    de IIS. Mantiene un maximo de `max_requests` peticiones por `window_seconds`
    por clave, devolviendo `False` cuando se supera el limite.
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, Tuple[float, int]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            window_start, count = self._requests.get(key, (now, 0))
            if now - window_start >= self.window_seconds:
                self._requests[key] = (now, 1)
                return True
            if count >= self.max_requests:
                return False
            self._requests[key] = (window_start, count + 1)
            return True

    def reset(self) -> None:
        """Limpia el estado interno (util para pruebas)."""
        with self._lock:
            self._requests.clear()


# Limite perimetral de 3 peticiones por minuto por IP en endpoints de auth (ADR-0019).
auth_rate_limiter = RateLimiter(max_requests=3, window_seconds=60)
catalog_rate_limiter = RateLimiter(max_requests=20, window_seconds=1)
cart_add_rate_limiter = RateLimiter(max_requests=5, window_seconds=1)
checkout_rate_limiter = RateLimiter(max_requests=3, window_seconds=60)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """Aplica el rate limit de 3 req/min por IP sobre los POST de auth (ADR-0019)."""

    def __init__(self, app, *, limiter: RateLimiter = None) -> None:
        super().__init__(app)
        self.limiter = limiter if limiter is not None else auth_rate_limiter

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "POST" and request.url.path in AUTH_POST_PATHS:
            if not self.limiter.allow(_client_ip(request)):
                return JSONResponse(status_code=429, content={"detail": RATE_LIMIT_DETAIL})
        return await call_next(request)


class CatalogRateLimitMiddleware(BaseHTTPMiddleware):
    """Limita busquedas de catalogo a 20 consultas por segundo e IP (ADR-0019)."""

    def __init__(self, app, *, limiter: RateLimiter = None) -> None:
        super().__init__(app)
        self.limiter = limiter if limiter is not None else catalog_rate_limiter

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "GET" and request.url.path == CATALOG_GET_PATH:
            if not self.limiter.allow(_client_ip(request)):
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Demasiadas consultas de catálogo. Intente nuevamente."
                    },
                )
        return await call_next(request)


class CartRateLimitMiddleware(BaseHTTPMiddleware):
    """Protege adición de guest y checkout contra abuso de reservas (ADR-0016)."""

    def __init__(self, app, *, add_limiter: RateLimiter = None, checkout_limiter: RateLimiter = None) -> None:
        super().__init__(app)
        settings = get_settings()
        self.add_limiter = add_limiter if add_limiter is not None else RateLimiter(
            settings.cart_add_burst, 1
        )
        self.checkout_limiter = (
            checkout_limiter
            if checkout_limiter is not None
            else RateLimiter(settings.checkout_rate_limit_per_minute, 60)
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "POST" and request.url.path == CART_ADD_PATH:
            if not self.add_limiter.allow(_client_ip(request)):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Demasiadas solicitudes. Por favor, intente nuevamente."},
                )
        if request.method == "POST" and request.url.path == CHECKOUT_PATH:
            if not self.checkout_limiter.allow(_client_ip(request)):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Demasiados inicios de checkout. Intente nuevamente."},
                )
        return await call_next(request)
