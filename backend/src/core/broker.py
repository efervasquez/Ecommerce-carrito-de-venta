import json
import logging
from typing import Any, Dict, Optional
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


async def publish_event(
    queue_name: str, payload: Dict[str, Any], timeout: float = 1.0
) -> None:
    """Publica un evento JSON en la cola indicada (cola duradera, entrega persistente).

    Usa una conexion de un solo uso con timeout corto (no robusta) para no acoplar la
    latencia ni el estado del broker a la peticion HTTP que lo invoca: si el broker
    esta caido, falla en ~1s sin dejar bucles de reconexion en segundo plano. Se
    declara la cola de forma idempotente y se publica en el exchange por defecto usando
    `queue_name` como routing key (topologia de colas directas segun ADR-0007).
    """
    settings = get_settings()
    connection = await aio_pika.connect(settings.rabbitmq_url, timeout=timeout)
    async with connection:
        channel = await connection.channel()
        await channel.declare_queue(queue_name, durable=True)
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=queue_name,
        )
