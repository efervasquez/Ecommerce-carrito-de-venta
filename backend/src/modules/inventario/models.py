"""Modelos de contingencia de inventario y productos locales (HU-10)."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.modules.auth.models import utcnow


class Producto(Base):
    """Ficha local de producto para operacion autonoma en contingencia."""

    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    componentes: Mapped[str] = mapped_column(String(255), nullable=False)
    precio_regular: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(8), nullable=False, default="PEN")
    descuento_porcentaje: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0
    )
    precios_bajos: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requiere_receta: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    presentacion: Mapped[str] = mapped_column(String(255), nullable=False)
    detalle: Mapped[str] = mapped_column(Text, nullable=False)
    imagen_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    metodos_entrega: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    contraindicaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    precauciones_advertencias: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    reacciones_adversas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )


class InventarioAjuste(Base):
    """Auditoria de ajustes manuales de stock (HU-10 crit.3)."""

    __tablename__ = "inventario_ajustes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("productos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    stock_anterior: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_nuevo: Mapped[int] = mapped_column(Integer, nullable=False)
    motivo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, index=True
    )
