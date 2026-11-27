"""Consumidor de la cola `ocr.procesar` (ADR-0007, ADR-0008)."""

import asyncio
import json
import logging

from src.config import get_settings
from src.core.broker import get_broker_connection
from src.core.database import get_sessionmaker
from src.modules.ocr.constants import QUEUE_NAME
from src.modules.ocr.service import OCRService

logger = logging.getLogger("worker.ocr")

_concurrencia = asyncio.Semaphore(2)


async def procesar_mensaje(cuerpo: bytes, servicio: OCRService) -> None:
    async with _concurrencia:
        payload = json.loads(cuerpo.decode("utf-8"))
        job_id = int(payload["job_id"])
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            await servicio.procesar_job(job_id, session=session)


async def consumir_ocr() -> None:
    settings = get_settings()
    connection = await get_broker_connection()
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=2)
    queue = await channel.declare_queue(QUEUE_NAME, durable=True)
    servicio = OCRService()
    logger.info("Consumidor %s listo (concurrencia 2)", QUEUE_NAME)
    try:
        async with queue.iterator() as iterator:
            async for mensaje in iterator:
                try:
                    await procesar_mensaje(mensaje.body, servicio)
                except Exception as exc:
                    logger.warning(
                        "No se pudo procesar job OCR desde la cola: %s",
                        type(exc).__name__,
                    )
                finally:
                    await mensaje.ack()
    except asyncio.CancelledError:
        logger.info("Consumidor OCR detenido.")
        raise
