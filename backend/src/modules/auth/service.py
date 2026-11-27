import asyncio
import logging
import re
import time
import uuid
from datetime import timedelta
from typing import Any, Dict, Optional, Set

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.core.broker import publish_event
from src.core.logging import get_correlation_id
from src.modules.auth.models import Usuario
from src.modules.auth.repository import AuthRepository
from src.modules.auth.security import (
    create_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    is_strong_password,
    utcnow,
    verify_password,
)

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

QUEUE_EMAIL_AUTH = "email.auth"
EVENTO_ACTIVACION = "auth.activacion_solicitada"
EVENTO_RECUPERACION = "auth.recuperacion_solicitada"

TOKEN_TTL_HOURS = 24
RECOVERY_TOKEN_TTL_HOURS = 1
COOLDOWN_MINUTES = 15
RECOVERY_DAILY_LIMIT = 3
MIN_REGISTRO_SECONDS = 0.2

MENSAJE_REGISTRO = (
    "Si el correo ingresado es válido, recibirás un enlace de activación en tu buzón."
)
MENSAJE_RECUPERACION = "Si el email existe, recibirás un correo"
MENSAJE_EMAIL_REQUERIDO = "El campo email es requerido."
MENSAJE_EMAIL_INVALIDO = "Formato de correo electrónico inválido"
MENSAJE_ACTIVACION_OK = "Cuenta activada exitosamente. Ya puedes iniciar sesión."
MENSAJE_TOKEN_INVALIDO = "El enlace de activación es inválido o ha expirado."
MENSAJE_TOKEN_RECUPERACION_INVALIDO = (
    "El enlace de recuperación es inválido o ha expirado."
)
MENSAJE_PASSWORD_DEBIL = (
    "La contraseña debe tener al menos 8 caracteres e incluir mayúsculas, "
    "minúsculas y números."
)
MENSAJE_LOGIN_FALLIDO = "Credenciales inválidas o cuenta no activada."
MENSAJE_SUSPENDIDO = "Cuenta suspendida. Por favor, contacte a soporte."
MENSAJE_NO_AUTENTICADO = "No autenticado o token inválido."
MENSAJE_TOKEN_EXPIRADO = "Token expirado. Inicie sesión nuevamente."
MENSAJE_RESTABLECIMIENTO_OK = (
    "Contraseña restablecida exitosamente. Ya puedes iniciar sesión."
)

# Hash ficticio para igualar el tiempo de respuesta ante emails inexistentes (anti-enumeracion).
_DUMMY_BCRYPT_HASH = hash_password("contrasena-ficticia-para-timing-constante")


class AuthService:
    """Logica de negocio de autoregistro, activacion, login y sesion (HU-01)."""

    def __init__(self, repository: Optional[AuthRepository] = None) -> None:
        self.repository = repository or AuthRepository()
        self._background_tasks: Set[asyncio.Task] = set()

    async def solicitar_registro(self, email: str, session: AsyncSession) -> str:
        started = time.monotonic()
        try:
            email = email.strip()
            if not email:
                raise HTTPException(status_code=422, detail=MENSAJE_EMAIL_REQUERIDO)
            if not EMAIL_RE.match(email):
                raise HTTPException(status_code=422, detail=MENSAJE_EMAIL_INVALIDO)

            usuario = await self.repository.get_usuario_by_email(session, email)

            if usuario is None:
                usuario = await self.repository.create_usuario(session, email)
                token, expira_en = await self._emitir_activacion(session, usuario.id)
                await session.commit()
                await self._publicar_activacion(email, token, expira_en)
            else:
                await session.commit()
                if not await self._cooldown_activo(session, usuario.id):
                    if usuario.estado == "pendiente_activacion":
                        token, expira_en = await self._emitir_activacion(
                            session, usuario.id, invalidar_previos=True
                        )
                        await session.commit()
                        await self._publicar_activacion(email, token, expira_en)

            return MENSAJE_REGISTRO
        finally:
            elapsed = time.monotonic() - started
            remaining = MIN_REGISTRO_SECONDS - elapsed
            if remaining > 0:
                await asyncio.sleep(remaining)

    async def activar_cuenta(
        self, token: str, password: str, session: AsyncSession
    ) -> str:
        if not is_strong_password(password):
            raise HTTPException(status_code=422, detail=MENSAJE_PASSWORD_DEBIL)

        token = token.strip()
        token_row = await self.repository.get_token_by_hash(
            session, hash_token(token), "activacion"
        )

        if (
            token_row is None
            or token_row.usado_en is not None
            or token_row.expira_en <= utcnow()
        ):
            raise HTTPException(status_code=400, detail=MENSAJE_TOKEN_INVALIDO)

        usuario = await self.repository.get_usuario_by_id(session, token_row.usuario_id)
        if usuario is None:
            raise HTTPException(status_code=400, detail=MENSAJE_TOKEN_INVALIDO)

        token_row.usado_en = utcnow()
        await self.repository.set_usuario_activo(session, usuario, hash_password(password))
        await self.repository.invalidate_unused_activation_tokens(
            session, usuario.id, exclude_token_id=token_row.id
        )
        await session.commit()

        return MENSAJE_ACTIVACION_OK

    async def solicitar_recuperacion(self, email: str, session: AsyncSession) -> str:
        """Solicita recuperación sin revelar existencia, cooldown ni cuota diaria."""
        started = time.monotonic()
        try:
            email = email.strip()
            if not email:
                raise HTTPException(status_code=422, detail=MENSAJE_EMAIL_REQUERIDO)
            if not EMAIL_RE.match(email):
                raise HTTPException(status_code=422, detail=MENSAJE_EMAIL_INVALIDO)

            usuario = await self.repository.get_usuario_by_email(session, email)
            if usuario is not None and usuario.estado == "activo":
                ultimo = await self.repository.get_latest_recovery_token(session, usuario.id)
                cooldown_activo = bool(
                    ultimo is not None
                    and ultimo.creado_en > utcnow() - timedelta(minutes=COOLDOWN_MINUTES)
                )
                solicitudes_diarias = await self.repository.count_recovery_tokens_since(
                    session,
                    usuario.id,
                    utcnow() - timedelta(hours=24),
                )
                if not cooldown_activo and solicitudes_diarias < RECOVERY_DAILY_LIMIT:
                    token, expira_en = await self._emitir_recuperacion(session, usuario.id)
                    await session.commit()
                    await self._publicar_recuperacion(email, token, expira_en)

            return MENSAJE_RECUPERACION
        finally:
            elapsed = time.monotonic() - started
            remaining = MIN_REGISTRO_SECONDS - elapsed
            if remaining > 0:
                await asyncio.sleep(remaining)

    async def restablecer_contrasena(
        self, token: str, password: str, session: AsyncSession
    ) -> str:
        if not is_strong_password(password):
            raise HTTPException(status_code=422, detail=MENSAJE_PASSWORD_DEBIL)

        token_row = await self.repository.get_token_by_hash(
            session, hash_token(token.strip()), "recuperacion"
        )
        if (
            token_row is None
            or token_row.usado_en is not None
            or token_row.expira_en <= utcnow()
        ):
            raise HTTPException(
                status_code=400, detail=MENSAJE_TOKEN_RECUPERACION_INVALIDO
            )

        usuario = await self.repository.get_usuario_by_id(session, token_row.usuario_id)
        if usuario is None:
            raise HTTPException(
                status_code=400, detail=MENSAJE_TOKEN_RECUPERACION_INVALIDO
            )

        token_row.usado_en = utcnow()
        await self.repository.set_usuario_password(session, usuario, hash_password(password))
        await self.repository.invalidate_unused_recovery_tokens(
            session, usuario.id, exclude_token_id=token_row.id
        )
        await session.commit()
        return MENSAJE_RESTABLECIMIENTO_OK

    async def login(self, email: str, password: str, session: AsyncSession) -> Dict[str, Any]:
        email = email.strip()
        usuario = await self.repository.get_usuario_by_email(session, email)

        if usuario is None:
            verify_password(password, _DUMMY_BCRYPT_HASH)
            raise HTTPException(status_code=401, detail=MENSAJE_LOGIN_FALLIDO)

        if usuario.estado == "suspendido":
            raise HTTPException(status_code=403, detail=MENSAJE_SUSPENDIDO)

        if usuario.estado != "activo":
            raise HTTPException(status_code=401, detail=MENSAJE_LOGIN_FALLIDO)

        if not usuario.password_hash or not verify_password(password, usuario.password_hash):
            raise HTTPException(status_code=401, detail=MENSAJE_LOGIN_FALLIDO)

        access_token = create_access_token(
            subject=str(usuario.id), rol=usuario.rol, scopes=[usuario.rol]
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": get_settings().jwt_expires_seconds,
            "usuario": {"id": usuario.id, "email": usuario.email, "rol": usuario.rol},
        }

    async def get_me(self, usuario_id: int, session: AsyncSession) -> Dict[str, Any]:
        usuario = await self.repository.get_usuario_by_id(session, usuario_id)
        if usuario is None:
            raise HTTPException(status_code=401, detail=MENSAJE_NO_AUTENTICADO)
        return {
            "id": usuario.id,
            "email": usuario.email,
            "rol": usuario.rol,
            "estado": usuario.estado,
        }

    async def _emitir_activacion(
        self,
        session: AsyncSession,
        usuario_id: int,
        *,
        invalidar_previos: bool = False,
    ):
        if invalidar_previos:
            await self.repository.invalidate_unused_activation_tokens(session, usuario_id)
        token = generate_opaque_token()
        expira_en = utcnow() + timedelta(hours=TOKEN_TTL_HOURS)
        await self.repository.create_token(
            session,
            usuario_id=usuario_id,
            token_hash=hash_token(token),
            tipo="activacion",
            expira_en=expira_en,
        )
        return token, expira_en

    async def _emitir_recuperacion(self, session: AsyncSession, usuario_id: int):
        await self.repository.invalidate_unused_recovery_tokens(session, usuario_id)
        token = generate_opaque_token()
        expira_en = utcnow() + timedelta(hours=RECOVERY_TOKEN_TTL_HOURS)
        await self.repository.create_token(
            session,
            usuario_id=usuario_id,
            token_hash=hash_token(token),
            tipo="recuperacion",
            expira_en=expira_en,
        )
        return token, expira_en

    async def _cooldown_activo(self, session: AsyncSession, usuario_id: int) -> bool:
        ultimo = await self.repository.get_latest_activation_token(session, usuario_id)
        if ultimo is None:
            return False
        limite = utcnow() - timedelta(minutes=COOLDOWN_MINUTES)
        return ultimo.creado_en > limite

    async def _publicar_activacion(
        self, email: str, token: str, expira_en
    ) -> None:
        # La publicacion al broker NO bloquea el request: se lanza en segundo plano
        # para no acoplar la latencia (ni el estado) de RabbitMQ a la respuesta HTTP,
        # preservando el anti-enumeracion de timing del contrato (seccion 3.1).
        payload = self._build_event(email, token, expira_en)
        task = asyncio.create_task(self._publish_in_background(payload))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _publicar_recuperacion(
        self, email: str, token: str, expira_en
    ) -> None:
        payload = self._build_recovery_event(email, token, expira_en)
        task = asyncio.create_task(self._publish_in_background(payload))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _publish_in_background(self, payload: Dict[str, Any]) -> None:
        try:
            await publish_event(QUEUE_EMAIL_AUTH, payload)
        except Exception as exc:
            logger.warning(f"No se pudo publicar evento de auth en RabbitMQ: {exc}")

    def _build_event(self, email: str, token: str, expira_en) -> Dict[str, Any]:
        settings = get_settings()
        correlation_id = get_correlation_id() or str(uuid.uuid4())
        return {
            "evento": EVENTO_ACTIVACION,
            "correlation_id": correlation_id,
            "timestamp": utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "payload": {
                "email": email,
                "token": token,
                "url_activacion": f"{settings.frontend_base_url}/activar?token={token}",
                "expira_en": expira_en.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        }

    def _build_recovery_event(
        self, email: str, token: str, expira_en
    ) -> Dict[str, Any]:
        settings = get_settings()
        correlation_id = get_correlation_id() or str(uuid.uuid4())
        return {
            "evento": EVENTO_RECUPERACION,
            "correlation_id": correlation_id,
            "timestamp": utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "payload": {
                "email": email,
                "token": token,
                "url_recuperacion": f"{settings.frontend_base_url}/restablecer?token={token}",
                "expira_en": expira_en.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        }
