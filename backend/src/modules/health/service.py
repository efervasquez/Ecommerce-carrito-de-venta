from typing import Optional, Tuple
from src.modules.health.repository import HealthRepository
from src.modules.health.schemas import HealthResponse


class HealthService:
    """Servicio de verificacion de estado de salud del sistema."""

    def __init__(self, repository: Optional[HealthRepository] = None) -> None:
        self.repository = repository or HealthRepository()

    async def get_health_status(self) -> Tuple[int, HealthResponse]:
        mysql_ok = await self.repository.check_mysql()
        rabbitmq_ok = await self.repository.check_rabbitmq()

        mysql_status = "connected" if mysql_ok else "disconnected"
        rabbitmq_status = "connected" if rabbitmq_ok else "disconnected"

        is_healthy = mysql_ok and rabbitmq_ok
        status_code = 200 if is_healthy else 503
        overall_status = "ok" if is_healthy else "unhealthy"

        return status_code, HealthResponse(
            status=overall_status,
            mysql=mysql_status,
            rabbitmq=rabbitmq_status,
        )
