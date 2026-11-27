from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Esquema de respuesta para el estado de salud del sistema."""

    model_config = ConfigDict(extra="ignore")

    status: str
    mysql: str
    rabbitmq: str
