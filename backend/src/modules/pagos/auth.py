"""Dependencia de autenticacion para los endpoints de pago y pedidos."""

from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.modules.auth.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)
UNAUTHENTICATED = "No autenticado o token inválido."


async def require_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> int:
    if credentials is None:
        raise HTTPException(status_code=401, detail=UNAUTHENTICATED)
    try:
        payload = decode_access_token(credentials.credentials)
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError, jwt.InvalidTokenError) as exc:
        raise HTTPException(status_code=401, detail=UNAUTHENTICATED) from exc
