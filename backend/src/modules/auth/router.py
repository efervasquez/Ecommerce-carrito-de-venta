from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.modules.auth.repository import AuthRepository
from src.modules.auth.schemas import (
    ActivacionRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    MensajeResponse,
    RegistroRequest,
)
from src.modules.auth.security import decode_access_token
from src.modules.auth.service import (
    AuthService,
    MENSAJE_NO_AUTENTICADO,
    MENSAJE_TOKEN_EXPIRADO,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

_bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service() -> AuthService:
    return AuthService(AuthRepository())


async def get_current_usuario_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> int:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail=MENSAJE_NO_AUTENTICADO)

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail=MENSAJE_TOKEN_EXPIRADO)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail=MENSAJE_NO_AUTENTICADO)

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail=MENSAJE_NO_AUTENTICADO)
    try:
        return int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail=MENSAJE_NO_AUTENTICADO)


@router.post("/registro", response_model=MensajeResponse)
async def registro(
    payload: RegistroRequest,
    session: AsyncSession = Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
) -> MensajeResponse:
    message = await service.solicitar_registro(payload.email, session)
    return MensajeResponse(message=message)


@router.post("/activar", response_model=MensajeResponse)
async def activar(
    payload: ActivacionRequest,
    session: AsyncSession = Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
) -> MensajeResponse:
    message = await service.activar_cuenta(payload.token, payload.password, session)
    return MensajeResponse(message=message)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    result = await service.login(payload.email, payload.password, session)
    return LoginResponse(**result)


@router.get("/me", response_model=MeResponse)
async def me(
    usuario_id: int = Depends(get_current_usuario_id),
    session: AsyncSession = Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
) -> MeResponse:
    result = await service.get_me(usuario_id, session)
    return MeResponse(**result)
