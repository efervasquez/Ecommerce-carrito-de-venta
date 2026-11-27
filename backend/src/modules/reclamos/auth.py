"""Enforcement RBAC para los endpoints de reclamos (HU-09, ADR-0004)."""

from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.modules.auth.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)

UNAUTHENTICATED = "No autenticado o token inválido."
FORBIDDEN = "No tienes permisos para realizar esta operación."
MSG_INSPECCION_FORBIDDEN = (
    "Solo el personal de reparto o administración puede registrar "
    "inspecciones en campo."
)


@dataclass(frozen=True)
class Principal:
    usuario_id: int
    rol: str


def _principal_from_credentials(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Principal:
    if credentials is None:
        raise HTTPException(status_code=401, detail=UNAUTHENTICATED)
    try:
        payload = decode_access_token(credentials.credentials)
        usuario_id = int(payload["sub"])
        rol = str(payload.get("rol", ""))
    except (KeyError, TypeError, ValueError, jwt.InvalidTokenError) as exc:
        raise HTTPException(status_code=401, detail=UNAUTHENTICATED) from exc
    return Principal(usuario_id=usuario_id, rol=rol)


def require_roles(*roles: str):
    """Exige sesion valida y uno de los roles indicados.

    401 sin token o token invalido; 403 si el rol no corresponde.
    """

    allowed = set(roles)

    async def dependency(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    ) -> Principal:
        principal = _principal_from_credentials(credentials)
        if principal.rol not in allowed:
            raise HTTPException(status_code=403, detail=FORBIDDEN)
        return principal

    return dependency


require_consulta = require_roles("cliente", "motorizado", "admin")
require_cliente = require_roles("cliente")


async def require_inspector(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Principal:
    """Inspeccion en campo: solo motorizado o admin, con mensaje contractual."""
    principal = _principal_from_credentials(credentials)
    if principal.rol not in {"motorizado", "admin"}:
        raise HTTPException(status_code=403, detail=MSG_INSPECCION_FORBIDDEN)
    return principal
