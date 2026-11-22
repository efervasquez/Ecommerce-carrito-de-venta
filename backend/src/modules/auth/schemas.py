from pydantic import BaseModel, ConfigDict


class RegistroRequest(BaseModel):
    """Peticion de autoregistro: unico campo de correo electronico (HU-01)."""

    model_config = ConfigDict(extra="ignore")

    email: str


class ActivacionRequest(BaseModel):
    """Peticion de activacion: token opaco + nueva contrasena del cliente."""

    model_config = ConfigDict(extra="ignore")

    token: str
    password: str


class LoginRequest(BaseModel):
    """Peticion de inicio de sesion con email y contrasena."""

    model_config = ConfigDict(extra="ignore")

    email: str
    password: str


class MensajeResponse(BaseModel):
    """Respuesta generica con un unico mensaje visible."""

    message: str


class UsuarioPublico(BaseModel):
    """Representacion publica del usuario dentro de la respuesta de login."""

    id: int
    email: str
    rol: str


class LoginResponse(BaseModel):
    """Respuesta de login con JWT de acceso y perfil del usuario (ADR-0004)."""

    access_token: str
    token_type: str
    expires_in: int
    usuario: UsuarioPublico


class MeResponse(BaseModel):
    """Perfil de la sesion activa (GET /api/v1/auth/me)."""

    id: int
    email: str
    rol: str
    estado: str
