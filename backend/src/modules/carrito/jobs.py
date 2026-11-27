import asyncio
import logging

from src.core.database import get_sessionmaker
from src.modules.carrito.service import CartService

logger = logging.getLogger(__name__)


async def release_expired_reservations() -> int:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        released = await CartService().release_expired(session)
        logger.info("Reservas expiradas liberadas", extra={"units": released})
        return released


def main() -> None:
    asyncio.run(release_expired_reservations())


if __name__ == "__main__":
    main()
