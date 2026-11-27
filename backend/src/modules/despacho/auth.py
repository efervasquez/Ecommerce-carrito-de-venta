"""Enforcement RBAC por rol para los endpoints de despacho (HU-08)."""

from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.modules.auth.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)

UNAUTHENTICATED = "No autenticado o token inválido."
FORBIDDEN = "No tienes permisos para realizar esta operación."

ROLES = ("cliente", "motorizado", "admin")


@dataclass(frozen=True)
class Principal:
    usuario_id: int
    rol: str


def require_roles(*roles: str):
    """Dependencia que exige sesion valida y uno de los roles indicados.

    401 si no hay sesion o el token es invalido; 403 si el rol no corresponde.
    """

    allowed = set(roles)

    async def dependency(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    ) -> Principal:
        if credentials is None:
            raise HTTPException(status_code=401, detail=UNAUTHENTICATED)
        try:
            payload = decode_access_token(credentials.credentials)
            usuario_id = int(payload["sub"])
            rol = str(payload.get("rol", ""))
        except (KeyError, TypeError, ValueError, jwt.InvalidTokenError) as exc:
            raise HTTPException(status_code=401, detail=UNAUTHENTICATED) from exc
        if rol not in allowed:
            raise HTTPException(status_code=403, detail=FORBIDDEN)
        return Principal(usuario_id=usuario_id, rol=rol)

    return dependency


require_admin = require_roles("admin")
require_motorizado = require_roles("motorizado")
require_admin_o_motorizado = require_roles("admin", "motorizado")
