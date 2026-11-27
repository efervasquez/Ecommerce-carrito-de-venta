import uuid
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.core.database import get_db_session
from src.modules.auth.security import decode_access_token
from src.modules.carrito.schemas import (
    CarritoItemInput,
    CarritoResponse,
    CantidadInput,
    CheckoutResponse,
)
from src.modules.carrito.service import CartActor, CartService

router = APIRouter(tags=["Carrito"])
_bearer = HTTPBearer(auto_error=False)
GUEST_COOKIE = "guest_session_id"


def get_cart_service() -> CartService:
    return CartService()


async def get_cart_actor(
    request: Request,
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> CartActor:
    user_id: Optional[int] = None
    if credentials is not None:
        try:
            payload = decode_access_token(credentials.credentials)
            user_id = int(payload["sub"])
        except (KeyError, TypeError, ValueError, jwt.InvalidTokenError) as exc:
            raise HTTPException(status_code=401, detail="No autenticado o token inválido.") from exc

    forwarded = request.headers.get("X-Forwarded-For")
    ip_address = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else "unknown")
    )
    if user_id is not None:
        return CartActor(
            session_id=f"user:{user_id}",
            user_id=user_id,
            ip_address=ip_address,
            is_guest=False,
        )

    session_id = request.cookies.get(GUEST_COOKIE)
    if not session_id:
        session_id = str(uuid.uuid4())
        settings = get_settings()
        response.set_cookie(
            GUEST_COOKIE,
            session_id,
            max_age=settings.cart_reservation_ttl_seconds,
            httponly=True,
            samesite="lax",
            secure=settings.app_env == "production",
        )
    return CartActor(
        session_id=session_id,
        user_id=None,
        ip_address=ip_address,
        is_guest=True,
    )


@router.get("/carrito", response_model=CarritoResponse)
async def get_cart(
    actor: CartActor = Depends(get_cart_actor),
    session: AsyncSession = Depends(get_db_session),
    service: CartService = Depends(get_cart_service),
) -> CarritoResponse:
    return await service.get_cart(session, actor)


@router.post("/carrito/items", response_model=CarritoResponse)
async def add_cart_item(
    payload: CarritoItemInput,
    actor: CartActor = Depends(get_cart_actor),
    session: AsyncSession = Depends(get_db_session),
    service: CartService = Depends(get_cart_service),
) -> CarritoResponse:
    return await service.add_item(session, actor, payload)


@router.patch("/carrito/items/{producto_id}", response_model=CarritoResponse)
async def update_cart_item(
    producto_id: int,
    payload: CantidadInput,
    actor: CartActor = Depends(get_cart_actor),
    session: AsyncSession = Depends(get_db_session),
    service: CartService = Depends(get_cart_service),
) -> CarritoResponse:
    return await service.update_item(session, actor, producto_id, payload)


@router.delete("/carrito/items/{producto_id}", response_model=CarritoResponse)
async def delete_cart_item(
    producto_id: int,
    actor: CartActor = Depends(get_cart_actor),
    session: AsyncSession = Depends(get_db_session),
    service: CartService = Depends(get_cart_service),
) -> CarritoResponse:
    return await service.delete_item(session, actor, producto_id)


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    actor: CartActor = Depends(get_cart_actor),
    session: AsyncSession = Depends(get_db_session),
    service: CartService = Depends(get_cart_service),
) -> CheckoutResponse:
    return await service.checkout_guest(session, actor)
