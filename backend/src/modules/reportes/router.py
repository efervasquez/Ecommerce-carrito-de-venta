"""Endpoints de reporteria del backoffice (HU-11)."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.modules.reportes.auth import Principal, require_reportero
from src.modules.reportes.schemas import (
    InventarioCritico,
    PedidoBalance,
    VentasReporte,
)
from src.modules.reportes.service import ReportesService

router = APIRouter(prefix="/backoffice/reportes", tags=["Backoffice Reportes"])


def get_reportes_service() -> ReportesService:
    return ReportesService()


@router.get("/ventas", response_model=VentasReporte)
async def reporte_ventas(
    fecha_inicio: Optional[str] = Query(default=None),
    fecha_fin: Optional[str] = Query(default=None),
    principal: Principal = Depends(require_reportero),
    session: AsyncSession = Depends(get_db_session),
    service: ReportesService = Depends(get_reportes_service),
) -> VentasReporte:
    return await service.ventas(session, principal, fecha_inicio, fecha_fin)


@router.get("/pedidos-balance", response_model=PedidoBalance)
async def reporte_pedidos_balance(
    principal: Principal = Depends(require_reportero),
    session: AsyncSession = Depends(get_db_session),
    service: ReportesService = Depends(get_reportes_service),
) -> PedidoBalance:
    return await service.balance(session, principal)


@router.get("/inventario-critico", response_model=InventarioCritico)
async def reporte_inventario_critico(
    principal: Principal = Depends(require_reportero),
    session: AsyncSession = Depends(get_db_session),
    service: ReportesService = Depends(get_reportes_service),
) -> InventarioCritico:
    return await service.inventario_critico(session, principal)
