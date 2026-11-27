"""DTOs de reporteria del backoffice (HU-11)."""

from pydantic import BaseModel


class VentasReporte(BaseModel):
    fecha_inicio: str
    fecha_fin: str
    total_ordenes: int
    unidades_vendidas: int
    monto_total_facturado: float
    moneda: str


class PedidoBalance(BaseModel):
    balance: dict[str, int]
    total_pedidos: int


class ProductoStockCritico(BaseModel):
    producto_id: int
    nombre: str
    stock_disponible: int


class ProductoRotacion(BaseModel):
    producto_id: int
    nombre: str
    unidades_vendidas: int


class InventarioCritico(BaseModel):
    stock_bajo: list[ProductoStockCritico]
    quiebres: list[ProductoStockCritico]
    mayor_rotacion: list[ProductoRotacion]
