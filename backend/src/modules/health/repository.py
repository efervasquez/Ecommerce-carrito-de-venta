import logging
from sqlalchemy import text
from src.core.broker import ping_broker
from src.core.database import get_engine

logger = logging.getLogger(__name__)


class HealthRepository:
    """Repositorio para verificar la conectividad con MySQL y RabbitMQ."""

    async def check_mysql(self) -> bool:
        try:
            engine = get_engine()
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as exc:
            logger.warning(f"Error comprobando estado de conexion MySQL: {exc}")
            return False

    async def check_rabbitmq(self) -> bool:
        try:
            return await ping_broker()
        except Exception as exc:
            logger.warning(f"Error comprobando estado de conexion RabbitMQ: {exc}")
            return False
