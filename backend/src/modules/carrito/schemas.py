from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CarritoItemInput(BaseModel):
    producto_id: int = Field(..., gt=0)
    cantidad: int = Field(..., ge=1)


class CantidadInput(BaseModel):
    cantidad: int = Field(..., ge=1)


class CarritoItemResponse(BaseModel):
    producto_id: int
    nombre: str
    imagen_url: Optional[str] = None
    cantidad: int
    precio_regular: float
    descuento_porcentaje: float
    precio_final: float
    subtotal: float
    ahorro: float
    stock_disponible: int


class CarritoResponse(BaseModel):
    items_oferta: list[CarritoItemResponse]
    items_regulares: list[CarritoItemResponse]
    subtotal: float
    ahorro_total: float
    total: float
    reserva_expira_en: Optional[datetime] = None


class CheckoutResponse(BaseModel):
    message: str
    reserva_expira_en: datetime
