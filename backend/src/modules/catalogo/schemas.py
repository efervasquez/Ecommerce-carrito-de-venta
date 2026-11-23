from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductoCatalogo(BaseModel):
    """Documento publico del modelo de lectura del catalogo."""

    model_config = ConfigDict(extra="ignore")

    id: int
    nombre: str
    componentes: str
    imagen_url: Optional[str] = None
    precio_regular: float
    moneda: str = "PEN"
    descuento_porcentaje: float = 0
    stock_disponible: int
    stock_bajo: bool
    precios_bajos: bool
    requiere_receta: bool


class CatalogoResponse(BaseModel):
    items: list[ProductoCatalogo]
    next_cursor: Optional[str] = None
    has_next: bool = False


class ProductoDetalle(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    nombre: str
    imagen_url: Optional[str] = None
    componentes: str
    precio_regular: float
    moneda: str = "PEN"
    descuento_porcentaje: float = 0
    requiere_receta: bool
    detalle: str
    presentacion: str
    metodos_entrega: list[str]
    contraindicaciones: str
    precauciones_advertencias: str
    reacciones_adversas: str
    precios_bajos: bool
    stock_disponible: int


class CatalogoQuery(BaseModel):
    """Parametros normalizados para la consulta de lectura."""

    q: str = ""
    cursor: Optional[str] = None
    limit: int = Field(..., ge=1, le=50)
