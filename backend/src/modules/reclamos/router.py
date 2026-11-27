"""Endpoints de reclamos y logistica inversa (HU-09)."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.modules.pagos.models import Pedido
from src.modules.reclamos.auth import (
    Principal,
    require_cliente,
    require_consulta,
    require_inspector,
    require_roles,
)
from src.modules.reclamos.models import Reclamo
from src.modules.reclamos.schemas import (
    InspeccionInput,
    InspeccionResponse,
    ReclamoItem,
    ReclamoListadoItem,
    ReclamoRegistroResponse,
)
from src.modules.reclamos.service import (
    MSG_REEMBOLSO_ACCION,
    MSG_REEMBOLSO_POLITICA,
    ReclamoService,
    _normalizar,
)

router = APIRouter(prefix="/reclamos", tags=["Reclamos"])


def get_reclamo_service() -> ReclamoService:
    return ReclamoService()


@router.post("", response_model=ReclamoRegistroResponse, status_code=201)
async def registrar_reclamo(
    pedido_numero: str = Form(...),
    producto_id: int = Form(...),
    motivo: str = Form(...),
    descripcion: Optional[str] = Form(default=None),
    foto_producto: Optional[UploadFile] = File(default=None),
    foto_comprobante: Optional[UploadFile] = File(default=None),
    principal: Principal = Depends(require_cliente),
    session: AsyncSession = Depends(get_db_session),
    service: ReclamoService = Depends(get_reclamo_service),
) -> ReclamoRegistroResponse:
    return await service.registrar(
        session,
        principal,
        pedido_numero=pedido_numero,
        producto_id=producto_id,
        motivo=motivo,
        descripcion=descripcion,
        foto_producto=foto_producto,
        foto_comprobante=foto_comprobante,
    )


@router.get("", response_model=list[ReclamoListadoItem])
async def listar_reclamos(
    estado: Optional[str] = Query(default=None),
    pedido_numero: Optional[str] = Query(default=None),
    principal: Principal = Depends(require_consulta),
    session: AsyncSession = Depends(get_db_session),
    service: ReclamoService = Depends(get_reclamo_service),
) -> list[ReclamoListadoItem]:
    return await service.listar(
        session, principal, estado=estado, pedido_numero=pedido_numero
    )


@router.get("/{reclamo_id}", response_model=ReclamoItem)
async def obtener_reclamo(
    reclamo_id: int,
    principal: Principal = Depends(require_consulta),
    session: AsyncSession = Depends(get_db_session),
    service: ReclamoService = Depends(get_reclamo_service),
) -> ReclamoItem:
    return await service.obtener(session, principal, reclamo_id)


@router.post(
    "/{reclamo_id}/inspeccion-campo",
    response_model=InspeccionResponse,
    response_model_exclude_none=True,
)
async def inspeccionar_reclamo(
    reclamo_id: int,
    payload: InspeccionInput,
    principal: Principal = Depends(require_inspector),
    session: AsyncSession = Depends(get_db_session),
    service: ReclamoService = Depends(get_reclamo_service),
) -> InspeccionResponse:
    return await service.inspeccionar(session, principal, reclamo_id, payload)


@router.post("/{reclamo_id}/reembolso")
async def bloquear_reembolso(
    reclamo_id: int,
    payload: Optional[dict] = Body(default=None),
    principal: Principal = Depends(
        require_roles("cliente", "motorizado", "admin")
    ),
) -> None:
    """Politica estricta de cero reembolsos (HU-09 crit.5)."""
    accion = ""
    if isinstance(payload, dict):
        accion = _normalizar(str(payload.get("accion", "")))
    if accion == "reembolso":
        raise HTTPException(status_code=400, detail=MSG_REEMBOLSO_ACCION)
    raise HTTPException(status_code=405, detail=MSG_REEMBOLSO_POLITICA)


@router.get("/{reclamo_id}/evidencias/{tipo}")
async def descargar_evidencia(
    reclamo_id: int,
    tipo: str,
    principal: Principal = Depends(require_consulta),
    session: AsyncSession = Depends(get_db_session),
) -> FileResponse:
    reclamo = await session.get(Reclamo, reclamo_id)
    if reclamo is None:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada.")
    origen = await session.get(Pedido, reclamo.pedido_origen_id)
    if origen is None:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada.")
    if principal.rol == "cliente" and int(origen.usuario_id) != principal.usuario_id:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada.")
    if principal.rol == "motorizado":
        reposicion = (
            await session.get(Pedido, reclamo.pedido_reposicion_id)
            if reclamo.pedido_reposicion_id is not None
            else None
        )
        asignado = (
            reposicion is not None
            and reposicion.motorizado_id is not None
            and int(reposicion.motorizado_id) == principal.usuario_id
        )
        if not asignado:
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para realizar esta operación.",
            )

    if tipo == "producto":
        ruta = Path(reclamo.foto_producto_path)
    elif tipo == "comprobante":
        ruta = Path(reclamo.foto_comprobante_path)
    else:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada.")
    if not ruta.is_file():
        raise HTTPException(status_code=404, detail="Evidencia no encontrada.")
    return FileResponse(ruta)
