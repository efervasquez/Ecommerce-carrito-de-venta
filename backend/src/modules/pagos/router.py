"""Routers de entrega, webhook de Stripe y consultas de pago/pedido."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.modules.pagos import gateway
from src.modules.pagos.auth import require_user_id
from src.modules.pagos.schemas import (
    DireccionInput,
    DireccionResponse,
    PagoEstadoResponse,
    PedidoResponse,
    WebhookResponse,
    ZonaResponse,
)
from src.modules.pagos.service import PagoService

router = APIRouter(tags=["Pagos"])


def get_pago_service() -> PagoService:
    return PagoService()


@router.get("/zonas", response_model=list[ZonaResponse])
async def listar_zonas(
    usuario_id: int = Depends(require_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: PagoService = Depends(get_pago_service),
) -> list[ZonaResponse]:
    return await service.listar_zonas(session)


@router.get("/direcciones", response_model=list[DireccionResponse])
async def listar_direcciones(
    usuario_id: int = Depends(require_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: PagoService = Depends(get_pago_service),
) -> list[DireccionResponse]:
    return await service.listar_direcciones(session, usuario_id)


@router.post("/direcciones", response_model=DireccionResponse, status_code=201)
async def crear_direccion(
    payload: DireccionInput,
    usuario_id: int = Depends(require_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: PagoService = Depends(get_pago_service),
) -> DireccionResponse:
    return await service.crear_direccion(session, usuario_id, payload)


@router.post("/pagos/webhook", response_model=WebhookResponse)
async def webhook_pagos(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    service: PagoService = Depends(get_pago_service),
) -> WebhookResponse:
    body = await request.body()
    if not gateway.verify_webhook_signature(body, request.headers.get("Stripe-Signature")):
        raise HTTPException(status_code=400, detail="Firma de webhook inválida.")
    try:
        evento = gateway.parse_webhook_event(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Evento de webhook inválido.") from exc
    procesado = await service.procesar_webhook(session, evento)
    return WebhookResponse(recibido=True, procesado=procesado)


@router.get("/pagos/{payment_intent_id}", response_model=PagoEstadoResponse)
async def estado_pago(
    payment_intent_id: str,
    usuario_id: int = Depends(require_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: PagoService = Depends(get_pago_service),
) -> PagoEstadoResponse:
    return await service.estado_pago(session, payment_intent_id, usuario_id)


@router.get("/pedidos/{numero}", response_model=PedidoResponse)
async def consultar_pedido(
    numero: str,
    usuario_id: int = Depends(require_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: PagoService = Depends(get_pago_service),
) -> PedidoResponse:
    return await service.obtener_pedido(session, numero, usuario_id)
