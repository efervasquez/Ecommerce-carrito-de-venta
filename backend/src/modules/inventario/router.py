"""Endpoints del backoffice de inventario y contingencia (HU-10)."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.modules.inventario.auth import Principal, require_admin
from src.modules.inventario.schemas import (
    ProductoCreateInput,
    ProductoDetalle,
    ProductoListadoResponse,
    ProductoUpdateInput,
    StockAjusteInput,
    StockAjusteResponse,
)
from src.modules.inventario.service import InventarioService

router = APIRouter(prefix="/backoffice/productos", tags=["Backoffice Inventario"])


def get_inventario_service() -> InventarioService:
    return InventarioService()


@router.get("", response_model=ProductoListadoResponse)
async def listar_productos(
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    service: InventarioService = Depends(get_inventario_service),
) -> ProductoListadoResponse:
    return await service.listar(session, q=q, limit=limit, offset=offset)


@router.get("/{producto_id}", response_model=ProductoDetalle)
async def obtener_producto(
    producto_id: int,
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    service: InventarioService = Depends(get_inventario_service),
) -> ProductoDetalle:
    return await service.detalle(session, producto_id)


@router.post("", response_model=ProductoDetalle, status_code=201)
async def crear_producto(
    payload: ProductoCreateInput,
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    service: InventarioService = Depends(get_inventario_service),
) -> ProductoDetalle:
    return await service.crear(session, principal, payload)


@router.put("/{producto_id}", response_model=ProductoDetalle)
async def actualizar_producto(
    producto_id: int,
    payload: ProductoUpdateInput,
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    service: InventarioService = Depends(get_inventario_service),
) -> ProductoDetalle:
    return await service.actualizar(session, principal, producto_id, payload)


@router.patch("/{producto_id}/stock", response_model=StockAjusteResponse)
async def ajustar_stock(
    producto_id: int,
    payload: StockAjusteInput,
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    service: InventarioService = Depends(get_inventario_service),
) -> StockAjusteResponse:
    return await service.ajustar_stock(session, principal, producto_id, payload)
