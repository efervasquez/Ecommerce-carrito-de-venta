import logging
from typing import Optional
import aio_pika
from aio_pika.abc import AbstractRobustConnection

from src.config import get_settings

logger = logging.getLogger(__name__)

_broker_connection: Optional[AbstractRobustConnection] = None


async def get_broker_connection() -> AbstractRobustConnection:
    """Obtiene o inicializa una conexion robusta asincrona a RabbitMQ."""
    global _broker_connection
    if _broker_connection is None or _broker_connection.is_closed:
        settings = get_settings()
        _broker_connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    return _broker_connection


async def close_broker_connection() -> None:
    """Cierra limpiamente la conexion al broker si estuviera abierta."""
    global _broker_connection
    if _broker_connection is not None and not _broker_connection.is_closed:
        await _broker_connection.close()
        _broker_connection = None


async def ping_broker() -> bool:
    """Verifica conectividad y apertura de canal en RabbitMQ."""
    try:
        connection = await get_broker_connection()
        channel = await connection.channel()
        await channel.close()
        return True
    except Exception as exc:
        logger.warning(f"Fallo de conectividad con broker RabbitMQ: {exc}")
        return False
