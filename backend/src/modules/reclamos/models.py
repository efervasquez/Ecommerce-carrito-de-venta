"""Modelos de logistica inversa, reclamos y mermas (HU-09)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.modules.auth.models import utcnow


class Reclamo(Base):
    """Reclamo de producto danado con evidencias y su pedido de reposicion."""

    __tablename__ = "reclamos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pedido_origen_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pedidos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pedido_reposicion_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("pedidos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    producto_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    foto_producto_url: Mapped[str] = mapped_column(String(512), nullable=False)
    foto_comprobante_url: Mapped[str] = mapped_column(String(512), nullable=False)
    foto_producto_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    foto_comprobante_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(32), nullable=False, default="aprobado", index=True
    )
    intentos_adicionales_realizados: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    comprobante_verificado: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    pertenencia_botica_verificada: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )
    defecto_fisico_verificado: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )
    motivo_falla: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, index=True
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )


class MermaAveriada(Base):
    """Asiento de descarte del producto recogido en campo (HU-09 crit.3)."""

    __tablename__ = "merma_averiada"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    reclamo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("reclamos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pedido_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("pedidos.id", ondelete="SET NULL"),
        nullable=True,
    )
    producto_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
