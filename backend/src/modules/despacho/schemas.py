"""DTOs del buzon de despacho y ciclo de vida de pedidos (HU-08)."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

EstadoPedidoManual = Literal["En camino", "Entregado"]


class PedidoDespachoItem(BaseModel):
    numero: str
    estado: str
    zona_id: int
    distrito: str
    metodo_entrega: str
    motorizado_id: Optional[int] = None
    monto: float
    creado_en: datetime


class ZonaDespachoResumen(BaseModel):
    zona_id: int
    nombre: str
    distrito: str
    pedidos_registrados: int
    pedidos_preparando: int
    pedidos_en_camino: int
    pedidos_entregados: int


class AsignacionInput(BaseModel):
    zona_id: int = Field(..., gt=0)
    pedido_numeros: list[str] = Field(..., min_length=1)
    motorizado_id: int = Field(..., gt=0)


class AsignacionResponse(BaseModel):
    zona_id: int
    motorizado_id: int
    asignados: list[str]


class EstadoPedidoInput(BaseModel):
    estado: EstadoPedidoManual


class HistorialEstadoItem(BaseModel):
    estado_anterior: Optional[str] = None
    estado_nuevo: str
    usuario_id: Optional[int] = None
    timestamp: datetime
