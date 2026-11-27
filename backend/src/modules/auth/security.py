import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import bcrypt
import jwt

from src.config import get_settings

JWT_ALGORITHM = "HS256"


def utcnow() -> datetime:
    """Timestamp UTC naive (para persistir en MySQL DATETIME)."""
    return datetime.utcnow()


def generate_opaque_token() -> str:
    """Token opaco UUID v4 generado con CSPRNG (ADR-0017)."""
    return str(uuid.uuid4())


def hash_token(token: str) -> str:
    """Hash SHA-256 del token; nunca se persiste el token en claro."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """Hash de contrasena con bcrypt (sal propia por hash)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Compara una contrasena en claro contra su hash bcrypt."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def is_strong_password(password: str) -> bool:
    """Politica DP-2: minimo 8 caracteres, 1 mayuscula, 1 minuscula y 1 numero."""
    if len(password) < 8:
        return False
    has_lower = any(char.islower() for char in password)
    has_upper = any(char.isupper() for char in password)
    has_digit = any(char.isdigit() for char in password)
    return has_lower and has_upper and has_digit


def create_access_token(subject: str, rol: str, scopes: list[str]) -> str:
    """Firma un JWT de acceso con claims RBAC: sub, rol, scopes y exp (ADR-0004)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "rol": rol,
        "scopes": scopes,
        "iat": now,
        "exp": now + timedelta(seconds=settings.jwt_expires_seconds),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodifica y verifica un JWT; lanza excepciones de PyJWT ante token invalido."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
