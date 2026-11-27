"""DTOs del backoffice de inventario y contingencia (HU-10)."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ProductoCreateInput(BaseModel):
    nombre: str
    componentes: str
    precio_regular: Any
    stock_disponible: Any
    presentacion: str
    detalle: str
    moneda: str = "PEN"
    metodos_entrega: Optional[list[str]] = None
    requiere_receta: bool = False
    imagen_url: Optional[str] = None
    descuento_porcentaje: Any = 0.0
    precios_bajos: bool = False
    contraindicaciones: Optional[str] = None
    precauciones_advertencias: Optional[str] = None
    reacciones_adversas: Optional[str] = None


class ProductoUpdateInput(BaseModel):
    nombre: str
    componentes: str
    precio_regular: Any
    presentacion: str
    detalle: str
    moneda: Optional[str] = None
    metodos_entrega: Optional[list[str]] = None
    requiere_receta: Optional[bool] = None
    imagen_url: Optional[str] = None
    descuento_porcentaje: Any = None
    precios_bajos: Optional[bool] = None
    contraindicaciones: Optional[str] = None
    precauciones_advertencias: Optional[str] = None
    reacciones_adversas: Optional[str] = None


class ProductoDetalle(BaseModel):
    id: int
    nombre: str
    componentes: str
    precio_regular: float
    moneda: str
    descuento_porcentaje: float
    precios_bajos: bool
    requiere_receta: bool
    presentacion: str
    detalle: str
    imagen_url: Optional[str] = None
    metodos_entrega: list[str]
    contraindicaciones: Optional[str] = None
    precauciones_advertencias: Optional[str] = None
    reacciones_adversas: Optional[str] = None
    stock_disponible: int
    stock_reservado: int
    creado_en: datetime
    actualizado_en: datetime


class ProductoListadoItem(BaseModel):
    id: int
    nombre: str
    componentes: str
    precio_regular: float
    descuento_porcentaje: float
    stock_disponible: int
    stock_reservado: int
    precios_bajos: bool
    requiere_receta: bool


class ProductoListadoResponse(BaseModel):
    items: list[ProductoListadoItem]
    total: int


class StockAjusteInput(BaseModel):
    stock_disponible: Any
    motivo: Optional[str] = None


class StockAjusteResponse(BaseModel):
    id: int
    producto_id: int
    disponible: int
    reservado: int
    actualizado_en: datetime
