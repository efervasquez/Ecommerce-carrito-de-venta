"""RBAC del backoffice de inventario (HU-10, ADR-0004)."""

from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.modules.auth.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)

UNAUTHENTICATED = "No autenticado o token inválido."
FORBIDDEN_INVENTARIO = (
    "Acceso restringido a operadores de inventario y administradores."
)


@dataclass(frozen=True)
class Principal:
    usuario_id: int
    rol: str


async def require_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Principal:
    """Exige sesion valida con rol admin; 401 sin token, 403 para el resto."""
    if credentials is None:
        raise HTTPException(status_code=401, detail=UNAUTHENTICATED)
    try:
        payload = decode_access_token(credentials.credentials)
        usuario_id = int(payload["sub"])
        rol = str(payload.get("rol", ""))
    except (KeyError, TypeError, ValueError, jwt.InvalidTokenError) as exc:
        raise HTTPException(status_code=401, detail=UNAUTHENTICATED) from exc
    if rol != "admin":
        raise HTTPException(status_code=403, detail=FORBIDDEN_INVENTARIO)
    return Principal(usuario_id=usuario_id, rol=rol)
