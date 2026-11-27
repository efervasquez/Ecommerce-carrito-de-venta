"""DTOs del modulo de reclamos y logistica inversa (ADR-0004)."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

EstadoReclamo = Literal[
    "aprobado",
    "reintento_pendiente",
    "cerrado_exitoso",
    "escalado_supervision",
]


class ReclamoRegistroResponse(BaseModel):
    id: int
    pedido_origen_numero: str
    pedido_reposicion_numero: str
    producto_id: int
    estado: str
    intentos_adicionales_realizados: int
    creado_en: datetime


class ReclamoListadoItem(BaseModel):
    """Estructura estandar de item para GET /api/v1/reclamos (v2)."""

    id: int
    pedido_origen_numero: str
    pedido_reposicion_numero: str
    producto_id: int
    estado: str
    intentos_adicionales_realizados: int
    creado_en: datetime


class ReclamoItem(BaseModel):
    id: int
    pedido_origen_numero: str
    pedido_reposicion_numero: Optional[str] = None
    pedido_reposicion_estado: Optional[str] = None
    producto_id: int
    motivo: str
    descripcion: Optional[str] = None
    estado: str
    intentos_adicionales_realizados: int
    intentos_restantes: int
    foto_producto_url: str
    foto_comprobante_url: str
    comprobante_verificado: Optional[bool] = None
    pertenencia_botica_verificada: Optional[bool] = None
    defecto_fisico_verificado: Optional[bool] = None
    motivo_falla: Optional[str] = None
    observaciones: Optional[str] = None
    creado_en: datetime
    actualizado_en: datetime


class InspeccionInput(BaseModel):
    resultado: Literal["conforme", "falla"]
    comprobante_verificado: bool
    pertenencia_botica_verificada: bool
    defecto_fisico_verificado: bool
    motivo_falla: Optional[str] = Field(default=None, max_length=255)
    observaciones: Optional[str] = None


class InspeccionResponse(BaseModel):
    id: int
    estado: str
    intentos_adicionales_realizados: Optional[int] = None
    intentos_restantes: Optional[int] = None
    mensaje: str
