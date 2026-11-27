"""Modelo de jobs OCR y recetas validadas (ADR-0008, ADR-0015)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.modules.auth.models import utcnow


class Receta(Base):
    """Job OCR: solo conserva el resultado estructurado, nunca el documento."""

    __tablename__ = "recetas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    estado: Mapped[str] = mapped_column(String(32), nullable=False, default="procesando")
    nombre_archivo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    receta_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    items_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sugeridos_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    faltantes_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confianza: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mensaje: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
