"""DTOs de jobs OCR y validación asistida (ADR-0004, HU-06)."""

from typing import Optional

from pydantic import BaseModel, Field


class JobCreadoResponse(BaseModel):
    job_id: int
    estado: str
    poll_interval_ms: int


class ItemReceta(BaseModel):
    producto_id: int
    nombre: str
    cantidad: int


class ItemSugerido(BaseModel):
    texto: str
    producto_id: Optional[int] = None
    cantidad: int
    confianza: float


class Faltante(BaseModel):
    nombre: str
    solicitado: int
    disponible: int


class JobResponse(BaseModel):
    estado: str
    receta_id: Optional[str] = None
    items: list[ItemReceta] = []
    items_sugeridos: list[ItemSugerido] = []
    faltantes: list[Faltante] = []
    confianza: Optional[float] = None
    mensaje: Optional[str] = None


class ConfirmarItem(BaseModel):
    producto_id: int = Field(..., gt=0)
    cantidad: int = Field(..., ge=1)


class ConfirmarInput(BaseModel):
    items: list[ConfirmarItem] = Field(..., min_length=1)


class SinStockResponse(BaseModel):
    estado: str = "sin_stock"
    faltantes: list[Faltante]
    mensaje: str
