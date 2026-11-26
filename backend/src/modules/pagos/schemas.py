"""DTOs de entrega, checkout de pago, webhook y consultas (ADR-0004)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ZonaResponse(BaseModel):
    id: int
    nombre: str
    distrito: str
    tiempo_estimado_min: int


class DireccionInput(BaseModel):
    direccion_linea1: str = Field(..., min_length=1)
    referencia: Optional[str] = None
    telefono_contacto: str = Field(..., min_length=1)
    zona_id: int = Field(..., gt=0)


class DireccionResponse(BaseModel):
    id: int
    direccion_linea1: str
    referencia: Optional[str] = None
    telefono_contacto: str
    zona_id: int


class CheckoutInput(BaseModel):
    direccion_id: Optional[int] = Field(default=None, gt=0)
    metodo_entrega: Optional[str] = None


class CheckoutPagoResponse(BaseModel):
    payment_intent_id: str
    client_secret: str
    monto: float
    moneda: str
    reserva_expira_en: datetime


class PedidoResumen(BaseModel):
    numero: str
    estado: str
    monto: float
    moneda: str


class PagoEstadoResponse(BaseModel):
    estado: str
    pedido: Optional[PedidoResumen] = None


class PedidoItemResponse(BaseModel):
    producto_id: int
    nombre: str
    cantidad: int
    precio_unitario: float
    subtotal: float


class PedidoResponse(BaseModel):
    numero: str
    estado: str
    items: list[PedidoItemResponse]
    monto: float
    moneda: str
    metodo_entrega: str
    entrega: str


class WebhookResponse(BaseModel):
    recibido: bool = True
    procesado: bool = False
