from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


def utcnow() -> datetime:
    """Timestamp UTC naive, usado como default para columnas DATETIME de MySQL."""
    return datetime.utcnow()


class Usuario(Base):
    """Entidad de usuario con RBAC y estados de cuenta (ADR-0003)."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rol: Mapped[str] = mapped_column(String(32), nullable=False, default="cliente")
    estado: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pendiente_activacion"
    )
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class Token(Base):
    """Token opaco de activacion/recuperacion con hash SHA-256 (ADR-0017)."""

    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expira_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    usado_en: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
