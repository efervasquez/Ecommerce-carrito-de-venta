"""Routers del buzon de despacho logistico (HU-08)."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.modules.despacho.auth import (
    Principal,
    require_admin,
    require_admin_o_motorizado,
    require_motorizado,
)
from src.modules.despacho.schemas import (
    AsignacionInput,
    AsignacionResponse,
    EstadoPedidoInput,
    HistorialEstadoItem,
    PedidoDespachoItem,
    ZonaDespachoResumen,
)
from src.modules.despacho.service import DespachoService

router = APIRouter(prefix="/despacho", tags=["Despacho"])


def get_despacho_service() -> DespachoService:
    return DespachoService()


@router.get("/pedidos", response_model=list[PedidoDespachoItem])
async def listar_pedidos(
    estado: Optional[str] = Query(default=None),
    zona_id: Optional[int] = Query(default=None),
    principal: Principal = Depends(require_admin_o_motorizado),
    session: AsyncSession = Depends(get_db_session),
    service: DespachoService = Depends(get_despacho_service),
) -> list[PedidoDespachoItem]:
    return await service.listar_pedidos(
        session,
        estado=estado,
        zona_id=zona_id,
        actor_id=principal.usuario_id,
        rol=principal.rol,
    )


@router.get("/zonas", response_model=list[ZonaDespachoResumen])
async def resumen_zonas(
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    service: DespachoService = Depends(get_despacho_service),
) -> list[ZonaDespachoResumen]:
    return await service.resumen_zonas(session)


@router.post("/asignaciones", response_model=AsignacionResponse)
async def asignar_lote(
    payload: AsignacionInput,
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    service: DespachoService = Depends(get_despacho_service),
) -> AsignacionResponse:
    return await service.asignar_lote(session, payload, principal.usuario_id)


@router.get("/pedidos/pendientes", response_model=list[PedidoDespachoItem])
async def pedidos_pendientes(
    zona_id: int = Query(...),
    principal: Principal = Depends(require_motorizado),
    session: AsyncSession = Depends(get_db_session),
    service: DespachoService = Depends(get_despacho_service),
) -> list[PedidoDespachoItem]:
    return await service.pendientes(session, zona_id)


@router.get("/pedidos/mios", response_model=list[PedidoDespachoItem])
async def mis_pedidos(
    principal: Principal = Depends(require_motorizado),
    session: AsyncSession = Depends(get_db_session),
    service: DespachoService = Depends(get_despacho_service),
) -> list[PedidoDespachoItem]:
    return await service.mis_pedidos(session, principal.usuario_id)


@router.post(
    "/pedidos/{numero}/auto-asignar", response_model=PedidoDespachoItem
)
async def auto_asignar(
    numero: str,
    principal: Principal = Depends(require_motorizado),
    session: AsyncSession = Depends(get_db_session),
    service: DespachoService = Depends(get_despacho_service),
) -> PedidoDespachoItem:
    return await service.auto_asignar(session, numero, principal.usuario_id)


@router.patch("/pedidos/{numero}/estado", response_model=PedidoDespachoItem)
async def cambiar_estado(
    numero: str,
    payload: EstadoPedidoInput,
    principal: Principal = Depends(require_motorizado),
    session: AsyncSession = Depends(get_db_session),
    service: DespachoService = Depends(get_despacho_service),
) -> PedidoDespachoItem:
    return await service.avanzar_estado(
        session, numero, payload, principal.usuario_id
    )


@router.get(
    "/pedidos/{numero}/historial", response_model=list[HistorialEstadoItem]
)
async def historial_pedido(
    numero: str,
    principal: Principal = Depends(require_admin_o_motorizado),
    session: AsyncSession = Depends(get_db_session),
    service: DespachoService = Depends(get_despacho_service),
) -> list[HistorialEstadoItem]:
    return await service.historial(
        session, numero, principal.usuario_id, principal.rol
    )
