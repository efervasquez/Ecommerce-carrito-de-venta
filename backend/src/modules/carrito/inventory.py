from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.models import utcnow
from src.modules.carrito.models import InventarioStock


class StockInsufficientError(Exception):
    def __init__(self, product_id: int, available: int) -> None:
        self.product_id = product_id
        self.available = available
        super().__init__(f"stock insuficiente para {product_id}: {available}")


class LocalMySQLInventoryProvider:
    """Fuente de verdad local de inventario; todas las mutaciones son transaccionales."""

    async def _get_row(
        self,
        session: AsyncSession,
        product_id: int,
        initial_stock: int,
        *,
        for_update: bool = False,
    ) -> InventarioStock:
        statement = select(InventarioStock).where(InventarioStock.producto_id == product_id)
        if for_update:
            statement = statement.with_for_update()
        result = await session.execute(statement)
        row = result.scalar_one_or_none()
        if row is None:
            row = InventarioStock(
                producto_id=product_id,
                disponible=max(0, initial_stock),
                reservado=0,
                actualizado_en=utcnow(),
            )
            session.add(row)
            await session.flush()
        return row

    async def get_available_stock(
        self, session: AsyncSession, product_id: int, initial_stock: int
    ) -> int:
        row = await self._get_row(session, product_id, initial_stock)
        return row.disponible

    async def reserve_stock_batch(
        self,
        session: AsyncSession,
        items: Iterable[tuple[int, int, int]],
    ) -> None:
        """Reserva (producto_id, cantidad, stock_inicial) de forma indivisible."""
        operations = sorted(items, key=lambda item: item[0])
        rows: dict[int, InventarioStock] = {}
        for product_id, _, initial_stock in operations:
            rows[product_id] = await self._get_row(
                session, product_id, initial_stock, for_update=True
            )
        for product_id, quantity, _ in operations:
            row = rows[product_id]
            if row.disponible < quantity:
                raise StockInsufficientError(product_id, row.disponible)
        now = utcnow()
        for product_id, quantity, _ in operations:
            row = rows[product_id]
            row.disponible -= quantity
            row.reservado += quantity
            row.actualizado_en = now
        await session.flush()

    async def release_reservation_batch(
        self,
        session: AsyncSession,
        items: Iterable[tuple[int, int]],
    ) -> None:
        operations = sorted(items, key=lambda item: item[0])
        for product_id, quantity in operations:
            result = await session.execute(
                select(InventarioStock)
                .where(InventarioStock.producto_id == product_id)
                .with_for_update()
            )
            row = result.scalar_one_or_none()
            if row is None:
                continue
            released = min(quantity, row.reservado)
            row.reservado -= released
            row.disponible += released
            row.actualizado_en = utcnow()
        await session.flush()
