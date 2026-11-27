import asyncio
import logging
import signal
import sys
from src.config import get_settings
from src.core.broker import close_broker_connection, get_broker_connection
from src.core.logging import setup_logging

logger = logging.getLogger("worker")


async def run_worker() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info(
        "Iniciando proceso worker de segundo plano - Botica la Luz",
        extra={"env": settings.app_env, "service": "background-worker"},
    )

    consumidor_ocr = None
    try:
        connection = await get_broker_connection()
        channel = await connection.channel()
        logger.info(
            "Worker conectado exitosamente al broker RabbitMQ. Liveness verificado.",
            extra={
                "status": "running",
                "broker": "connected",
                "rabbitmq_url": settings.rabbitmq_url,
            },
        )
        await channel.close()

        if settings.ocr_worker_enabled:
            from src.workers.ocr_consumer import consumir_ocr

            consumidor_ocr = asyncio.create_task(consumir_ocr())
            logger.info("Consumidor de cola OCR iniciado.")

        # En Sprint 0 no hay colas ni consumidores de negocio (ADR-0007 / SPRINT0.md).
        # El proceso valida conectividad y queda listo para ejecucion continua.
        stop_event = asyncio.Event()

        def handle_signal(*_: object) -> None:
            logger.info("Senal de parada recibida en worker. Finalizando...")
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop = asyncio.get_running_loop()
                loop.add_signal_handler(sig, handle_signal)
            except (NotImplementedError, AttributeError):
                # Soporte de senales en Windows
                pass

        logger.info("Worker en espera activa de tareas y senales de terminacion.")

        # Flag opcional para pruebas y verificacion rapida sin bloqueo indefinido
        if "--once" in sys.argv:
            logger.info("Modo --once detectado. Finalizando tras verificacion de liveness exitosa.")
            return

        try:
            while not stop_event.is_set():
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    except Exception as exc:
        logger.error(
            f"Fallo critico en proceso worker al conectar con RabbitMQ: {exc}",
            exc_info=True,
        )
        sys.exit(1)
    finally:
        if consumidor_ocr is not None and not consumidor_ocr.done():
            consumidor_ocr.cancel()
            try:
                await consumidor_ocr
            except asyncio.CancelledError:
                pass
        logger.info("Cerrando conexion de worker con broker...")
        await close_broker_connection()
        logger.info("Proceso worker finalizado ordenadamente.")


def main() -> None:
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker detenido por teclado.")


if __name__ == "__main__":
    main()
