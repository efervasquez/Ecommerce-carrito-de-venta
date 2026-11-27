"""Seed idempotente de usuarios de backoffice (admin y motorizado) para HU-08.

Las credenciales se leen de variables de entorno; no hay valores por defecto
hardcodeados. El seed se ejecuta al iniciar la app en entornos de prueba, en el
primer request (tambien bajo ASGITransport, que no dispara el lifespan) o de forma
explicita con SEED_RBAC_USERS=true.
"""

import asyncio
import logging
import os
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.core.database import get_sessionmaker
from src.modules.auth.models import Usuario
from src.modules.auth.security import hash_password

logger = logging.getLogger(__name__)

_TEST_ENVS = {"test", "testing"}

_seed_lock = asyncio.Lock()
_seeded_signature: Optional[tuple] = None


def _credential(env_name: str, setting_value: str) -> str:
    """Prioriza os.environ para no depender del cache de settings en pruebas."""
    return (os.environ.get(env_name) or setting_value or "").strip()


def seed_enabled() -> bool:
    settings = get_settings()
    env_values = {
        settings.app_env.lower(),
        os.environ.get("APP_ENV", "").lower(),
        os.environ.get("ENVIRONMENT", "").lower(),
    }
    if env_values & _TEST_ENVS:
        return True
    return settings.seed_rbac_users


def _seed_accounts() -> list[tuple[str, str, str]]:
    settings = get_settings()
    candidates = (
        (
            _credential("SEED_ADMIN_EMAIL", settings.seed_admin_email),
            _credential("SEED_ADMIN_PASSWORD", settings.seed_admin_password),
            "admin",
        ),
        (
            _credential("SEED_MOTORIZADO_EMAIL", settings.seed_motorizado_email),
            _credential("SEED_MOTORIZADO_PASSWORD", settings.seed_motorizado_password),
            "motorizado",
        ),
    )
    return [(email, password, rol) for email, password, rol in candidates if email and password]


async def seed_rbac_users(session: AsyncSession) -> list[str]:
    """Crea o actualiza de forma idempotente los usuarios admin/motorizado.

    Si una credencial falta en el entorno, ese usuario se omite. Devuelve los
    emails sembrados. No se registra la contrasena en logs.
    """
    sembrados: list[str] = []
    for email, password, rol in _seed_accounts():
        usuario: Optional[Usuario] = await session.scalar(
            select(Usuario).where(Usuario.email == email)
        )
        if usuario is None:
            usuario = Usuario(
                email=email,
                rol=rol,
                estado="activo",
                password_hash=hash_password(password),
            )
            session.add(usuario)
        else:
            usuario.rol = rol
            usuario.estado = "activo"
            usuario.password_hash = hash_password(password)
        sembrados.append(email)
    if sembrados:
        await session.commit()
    return sembrados


async def ensure_seed_users() -> list[str]:
    """Abre una sesion propia y ejecuta el seed idempotente."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            return await seed_rbac_users(session)
        except Exception:
            await session.rollback()
            raise


async def ensure_seed_users_once() -> None:
    """Aplica el seed cuando cambian las credenciales configuradas por entorno.

    No se marca como completado si no hay credenciales, de modo que un proceso que
    arranco sin SEED_* puede sembrar en un request posterior cuando las variables
    aparecen (p. ej. fixtures de pruebas por modulo).
    """
    global _seeded_signature
    if not seed_enabled():
        return
    accounts = _seed_accounts()
    if not accounts:
        return
    signature = tuple((email, rol, password) for email, password, rol in accounts)
    if _seeded_signature == signature:
        return
    async with _seed_lock:
        if _seeded_signature == signature:
            return
        try:
            emails = await ensure_seed_users()
            _seeded_signature = signature
            if emails:
                logger.info("Seed RBAC aplicado para %s usuarios de backoffice", len(emails))
        except Exception as exc:  # pragma: no cover - se reintenta en el siguiente request
            logger.warning("No se pudo aplicar el seed RBAC: %s", type(exc).__name__)


class SeedRbacMiddleware:
    """Middleware ASGI puro: no cancela las tareas en segundo plano del request."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http":
            await ensure_seed_users_once()
        await self.app(scope, receive, send)


async def _main() -> None:
    emails = await ensure_seed_users()
    print(f"Usuarios sembrados/actualizados: {', '.join(emails) if emails else 'ninguno'}")


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(_main())
