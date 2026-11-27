from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.modules.auth.models import utcnow


class Sesion(Base):
    __tablename__ = "sesiones"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    expira_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Carrito(Base):
    __tablename__ = "carritos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sesion_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sesiones.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    estado: Mapped[str] = mapped_column(String(24), nullable=False, default="activo")
    reserva_expira_en: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class CarritoItem(Base):
    __tablename__ = "carrito_items"
    __table_args__ = (UniqueConstraint("carrito_id", "producto_id", name="uq_carrito_producto"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    carrito_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("carritos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    producto_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_reservada: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    precio_unitario: Mapped[float] = mapped_column(nullable=False)
    descuento_porcentaje: Mapped[float] = mapped_column(nullable=False, default=0)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class InventarioStock(Base):
    __tablename__ = "inventario_stock"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    disponible: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reservado: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
