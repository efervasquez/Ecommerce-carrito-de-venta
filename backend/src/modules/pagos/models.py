"""Modelos de entrega, pedidos y pagos (ADR-0003, ADR-0013)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.modules.auth.models import utcnow


class Zona(Base):
    __tablename__ = "zonas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    distrito: Mapped[str] = mapped_column(String(120), nullable=False)
    tiempo_estimado_min: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class Direccion(Base):
    __tablename__ = "direcciones"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    zona_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("zonas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    direccion_linea1: Mapped[str] = mapped_column(String(255), nullable=False)
    referencia: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telefono_contacto: Mapped[str] = mapped_column(String(32), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    numero: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    carrito_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("carritos.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    direccion_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("direcciones.id", ondelete="SET NULL"), nullable=True
    )
    zona_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("zonas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    metodo_entrega: Mapped[str] = mapped_column(String(16), nullable=False)
    receta_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("recetas.id", ondelete="SET NULL"), nullable=True
    )
    auditoria_receta_pendiente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tipo: Mapped[str] = mapped_column(String(16), nullable=False, default="venta")
    estado: Mapped[str] = mapped_column(String(32), nullable=False, default="Registrado")
    monto: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(8), nullable=False, default="PEN")
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class PedidoItem(Base):
    __tablename__ = "pedido_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pedido_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    producto_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)


class Pago(Base):
    __tablename__ = "pagos"
    __table_args__ = (UniqueConstraint("idempotencia_key", name="uq_pago_idempotencia"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    payment_intent_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    idempotencia_key: Mapped[str] = mapped_column(String(255), nullable=False)
    carrito_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("carritos.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    intento: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    direccion_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("direcciones.id", ondelete="SET NULL"), nullable=True
    )
    zona_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("zonas.id", ondelete="RESTRICT"), nullable=False
    )
    metodo_entrega: Mapped[str] = mapped_column(String(16), nullable=False, default="retiro")
    monto: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(8), nullable=False, default="PEN")
    estado: Mapped[str] = mapped_column(String(16), nullable=False, default="procesando")
    pedido_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("pedidos.id", ondelete="SET NULL"), nullable=True
    )
    creado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
