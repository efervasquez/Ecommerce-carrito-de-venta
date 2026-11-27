"""Modelos del modulo de despacho logistico (HU-08)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.modules.auth.models import utcnow


class PedidoEstadoHistorial(Base):
    """Auditoria de cada transicion de estado de un pedido (HU-08 crit.5)."""

    __tablename__ = "pedido_estado_historial"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pedido_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pedidos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    estado_anterior: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    estado_nuevo: Mapped[str] = mapped_column(String(32), nullable=False)
    usuario_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, index=True
    )
