from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.models import Token, Usuario
from src.modules.auth.security import utcnow


class AuthRepository:
    """Acceso a datos de usuarios y tokens (capa Repository)."""

    async def get_usuario_by_email(
        self, session: AsyncSession, email: str
    ) -> Optional[Usuario]:
        result = await session.execute(select(Usuario).where(Usuario.email == email))
        return result.scalar_one_or_none()

    async def get_usuario_by_id(
        self, session: AsyncSession, usuario_id: int
    ) -> Optional[Usuario]:
        result = await session.execute(select(Usuario).where(Usuario.id == usuario_id))
        return result.scalar_one_or_none()

    async def create_usuario(self, session: AsyncSession, email: str) -> Usuario:
        usuario = Usuario(email=email, rol="cliente", estado="pendiente_activacion")
        session.add(usuario)
        await session.flush()
        return usuario

    async def create_token(
        self,
        session: AsyncSession,
        *,
        usuario_id: int,
        token_hash: str,
        tipo: str,
        expira_en: datetime,
    ) -> Token:
        token = Token(
            token_hash=token_hash,
            tipo=tipo,
            usuario_id=usuario_id,
            expira_en=expira_en,
        )
        session.add(token)
        await session.flush()
        return token

    async def get_token_by_hash(
        self, session: AsyncSession, token_hash: str, tipo: str
    ) -> Optional[Token]:
        result = await session.execute(
            select(Token).where(Token.token_hash == token_hash, Token.tipo == tipo)
        )
        return result.scalar_one_or_none()

    async def get_latest_activation_token(
        self, session: AsyncSession, usuario_id: int
    ) -> Optional[Token]:
        result = await session.execute(
            select(Token)
            .where(Token.usuario_id == usuario_id, Token.tipo == "activacion")
            .order_by(Token.creado_en.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def invalidate_unused_activation_tokens(
        self, session: AsyncSession, usuario_id: int, exclude_token_id: Optional[int] = None
    ) -> None:
        """Marca como usados los tokens de activacion pendientes de un usuario."""
        stmt = (
            update(Token)
            .where(
                Token.usuario_id == usuario_id,
                Token.tipo == "activacion",
                Token.usado_en.is_(None),
            )
            .values(usado_en=utcnow())
        )
        if exclude_token_id is not None:
            stmt = stmt.where(Token.id != exclude_token_id)
        await session.execute(stmt)

    async def set_usuario_activo(
        self, session: AsyncSession, usuario: Usuario, password_hash: str
    ) -> None:
        usuario.estado = "activo"
        usuario.password_hash = password_hash
        await session.flush()
