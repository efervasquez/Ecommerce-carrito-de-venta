import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.modules.auth.models import utcnow
from src.modules.catalogo.repository import CatalogReadRepository, ProductNotFoundError
from src.modules.carrito.inventory import LocalMySQLInventoryProvider, StockInsufficientError
from src.modules.carrito.models import Carrito, CarritoItem, Sesion
from src.modules.carrito.schemas import (
    CarritoItemInput,
    CarritoItemResponse,
    CarritoResponse,
    CantidadInput,
    CheckoutResponse,
)

MAX_UNITS_MESSAGE = "Límite máximo de 3 unidades por producto"
GUEST_PRODUCTS_MESSAGE = "Límite máximo de 10 productos distintos"
STOCK_MESSAGE = "Stock máximo disponible alcanzado ({units} unidades)"
CHECKOUT_MESSAGE = "Reserva creada exitosamente."


@dataclass(frozen=True)
class CartActor:
    session_id: str
    user_id: Optional[int]
    ip_address: str
    is_guest: bool


class CartService:
    def __init__(
        self,
        inventory: Optional[LocalMySQLInventoryProvider] = None,
        catalog: Optional[CatalogReadRepository] = None,
    ) -> None:
        self.inventory = inventory or LocalMySQLInventoryProvider()
        self.catalog = catalog or CatalogReadRepository()

    async def get_cart(self, session: AsyncSession, actor: CartActor) -> CarritoResponse:
        cart = await self._get_or_create_cart(session, actor)
        await self._purge_if_expired(session, cart)
        await session.commit()
        return await self._to_response(session, cart)

    async def add_item(
        self, session: AsyncSession, actor: CartActor, payload: CarritoItemInput
    ) -> CarritoResponse:
        cart = await self._get_or_create_cart(session, actor)
        await self._purge_if_expired(session, cart)
        product = await self._get_product(payload.producto_id)
        item = await self._get_item(session, cart.id, payload.producto_id, lock=True)
        current_quantity = item.cantidad if item else 0
        new_quantity = current_quantity + payload.cantidad
        self._validate_quantity(new_quantity)
        if actor.is_guest and item is None:
            count = await self._count_distinct_items(session, cart.id)
            if count >= get_settings().guest_max_distinct_products:
                raise HTTPException(status_code=409, detail=GUEST_PRODUCTS_MESSAGE)
        await self._apply_quantity(session, actor, cart, item, product, new_quantity)
        await session.commit()
        return await self._to_response(session, cart)

    async def update_item(
        self,
        session: AsyncSession,
        actor: CartActor,
        product_id: int,
        payload: CantidadInput,
    ) -> CarritoResponse:
        cart = await self._get_or_create_cart(session, actor)
        await self._purge_if_expired(session, cart)
        product = await self._get_product(product_id)
        item = await self._get_item(session, cart.id, product_id, lock=True)
        if item is None:
            raise HTTPException(status_code=404, detail="Producto inexistente en carrito.")
        self._validate_quantity(payload.cantidad)
        await self._apply_quantity(session, actor, cart, item, product, payload.cantidad)
        await session.commit()
        return await self._to_response(session, cart)

    async def delete_item(
        self, session: AsyncSession, actor: CartActor, product_id: int
    ) -> CarritoResponse:
        cart = await self._get_or_create_cart(session, actor)
        item = await self._get_item(session, cart.id, product_id, lock=True)
        if item is None:
            raise HTTPException(status_code=404, detail="Producto inexistente en carrito.")
        if item.cantidad_reservada:
            await self.inventory.release_reservation_batch(
                session, [(product_id, item.cantidad_reservada)]
            )
        await session.delete(item)
        remaining = await self._get_items(session, cart.id)
        if not remaining:
            cart.reserva_expira_en = None
            cart.estado = "activo"
        await session.commit()
        return await self._to_response(session, cart)

    async def checkout_guest(
        self, session: AsyncSession, actor: CartActor
    ) -> CheckoutResponse:
        cart = await self._get_or_create_cart(session, actor)
        await self._purge_if_expired(session, cart)
        items = await self._get_items(session, cart.id, lock=True)
        if not items:
            raise HTTPException(status_code=409, detail="El carrito está vacío.")
        if not actor.is_guest:
            if cart.reserva_expira_en is None:
                raise HTTPException(status_code=409, detail="La sesión autenticada no tiene reserva.")
            return CheckoutResponse(
                message=CHECKOUT_MESSAGE, reserva_expira_en=cart.reserva_expira_en
            )
        await self._ensure_guest_checkout_limit(session, actor, cart.id)
        operations = []
        for item in items:
            pending = item.cantidad - item.cantidad_reservada
            if pending > 0:
                product = await self._get_product(item.producto_id)
                operations.append((item.producto_id, pending, product["stock_disponible"]))
        try:
            if operations:
                await self.inventory.reserve_stock_batch(session, operations)
                for item in items:
                    item.cantidad_reservada = item.cantidad
            expires = utcnow() + timedelta(seconds=get_settings().cart_reservation_ttl_seconds)
            cart.reserva_expira_en = expires
            cart.estado = "reservado"
            await session.commit()
            return CheckoutResponse(message=CHECKOUT_MESSAGE, reserva_expira_en=expires)
        except StockInsufficientError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=409,
                detail=STOCK_MESSAGE.format(units=exc.available),
            ) from exc

    async def release_expired(self, session: AsyncSession) -> int:
        now = utcnow()
        result = await session.execute(
            select(Carrito).where(
                Carrito.reserva_expira_en.is_not(None), Carrito.reserva_expira_en <= now
            )
        )
        carts = list(result.scalars().all())
        released = 0
        for cart in carts:
            items = await self._get_items(session, cart.id, lock=True)
            reservations = [
                (item.producto_id, item.cantidad_reservada)
                for item in items
                if item.cantidad_reservada
            ]
            if reservations:
                await self.inventory.release_reservation_batch(session, reservations)
                released += sum(quantity for _, quantity in reservations)
            await session.execute(delete(CarritoItem).where(CarritoItem.carrito_id == cart.id))
            await session.delete(cart)
        await session.commit()
        return released

    async def _apply_quantity(self, session, actor, cart, item, product, new_quantity):
        settings = get_settings()
        available = await self.inventory.get_available_stock(
            session, product["id"], product["stock_disponible"]
        )
        if new_quantity > available + (item.cantidad_reservada if item else 0):
            raise HTTPException(
                status_code=409, detail=STOCK_MESSAGE.format(units=available)
            )
        if item is None:
            item = CarritoItem(
                carrito_id=cart.id,
                producto_id=product["id"],
                cantidad=new_quantity,
                cantidad_reservada=0,
                precio_unitario=product["precio_regular"],
                descuento_porcentaje=product["descuento_porcentaje"],
            )
            session.add(item)
        else:
            item.cantidad = new_quantity
        if not actor.is_guest:
            old_reserved = item.cantidad_reservada
            delta = new_quantity - old_reserved
            if delta > 0:
                try:
                    await self.inventory.reserve_stock_batch(
                        session, [(product["id"], delta, product["stock_disponible"])]
                    )
                except StockInsufficientError as exc:
                    raise HTTPException(
                        status_code=409, detail=STOCK_MESSAGE.format(units=exc.available)
                    ) from exc
            elif delta < 0:
                await self.inventory.release_reservation_batch(
                    session, [(product["id"], -delta)]
                )
            item.cantidad_reservada = new_quantity
            cart.reserva_expira_en = utcnow() + timedelta(
                seconds=settings.cart_reservation_ttl_seconds
            )
            cart.estado = "reservado"
        await session.flush()

    async def _get_product(self, product_id: int):
        try:
            return await self.catalog.get_by_id(product_id)
        except ProductNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Producto no encontrado.") from exc

    async def _get_or_create_cart(self, session, actor: CartActor) -> Carrito:
        result = await session.execute(
            select(Sesion).where(Sesion.id == actor.session_id).with_for_update()
        )
        session_row = result.scalar_one_or_none()
        if session_row is None:
            session_row = Sesion(
                id=actor.session_id,
                usuario_id=actor.user_id,
                ip_address=actor.ip_address,
                creado_en=utcnow(),
                expira_en=utcnow() + timedelta(seconds=get_settings().cart_reservation_ttl_seconds),
            )
            session.add(session_row)
            await session.flush()
        result = await session.execute(
            select(Carrito).where(Carrito.sesion_id == actor.session_id).with_for_update()
        )
        cart = result.scalar_one_or_none()
        if cart is None:
            cart = Carrito(sesion_id=actor.session_id, creado_en=utcnow())
            session.add(cart)
            await session.flush()
        return cart

    async def _purge_if_expired(self, session, cart: Carrito) -> None:
        if cart.reserva_expira_en is None or cart.reserva_expira_en > utcnow():
            return
        items = await self._get_items(session, cart.id, lock=True)
        reservations = [
            (item.producto_id, item.cantidad_reservada)
            for item in items
            if item.cantidad_reservada
        ]
        if reservations:
            await self.inventory.release_reservation_batch(session, reservations)
        for item in items:
            await session.delete(item)
        cart.reserva_expira_en = None
        cart.estado = "activo"
        await session.flush()

    async def _ensure_guest_checkout_limit(self, session, actor: CartActor, current_cart_id: int):
        now = utcnow()
        result = await session.execute(
            select(Carrito, Sesion)
            .join(Sesion, Sesion.id == Carrito.sesion_id)
            .where(
                Sesion.usuario_id.is_(None),
                Sesion.ip_address == actor.ip_address,
                Carrito.id != current_cart_id,
                Carrito.reserva_expira_en.is_not(None),
                Carrito.reserva_expira_en > now,
            )
        )
        if result.first() is not None:
            raise HTTPException(
                status_code=409,
                detail="Ya existe un checkout guest activo para esta IP.",
            )

    async def _get_item(self, session, cart_id: int, product_id: int, *, lock: bool = False):
        statement = select(CarritoItem).where(
            CarritoItem.carrito_id == cart_id, CarritoItem.producto_id == product_id
        )
        if lock:
            statement = statement.with_for_update()
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def _get_items(self, session, cart_id: int, *, lock: bool = False):
        statement = select(CarritoItem).where(CarritoItem.carrito_id == cart_id)
        if lock:
            statement = statement.with_for_update()
        result = await session.execute(statement)
        return list(result.scalars().all())

    async def _count_distinct_items(self, session, cart_id: int) -> int:
        result = await session.execute(
            select(func.count(CarritoItem.id)).where(CarritoItem.carrito_id == cart_id)
        )
        return int(result.scalar_one())

    @staticmethod
    def _validate_quantity(quantity: int) -> None:
        if quantity > get_settings().guest_max_units_per_sku:
            raise HTTPException(status_code=409, detail=MAX_UNITS_MESSAGE)

    async def _to_response(self, session, cart: Carrito) -> CarritoResponse:
        items = await self._get_items(session, cart.id)
        response_items = []
        for item in items:
            product = await self._get_product(item.producto_id)
            available = await self.inventory.get_available_stock(
                session, item.producto_id, product["stock_disponible"]
            )
            regular = float(item.precio_unitario)
            discount = float(item.descuento_porcentaje)
            final = round(regular * (1 - discount / 100), 2)
            response_items.append(
                CarritoItemResponse(
                    producto_id=item.producto_id,
                    nombre=product["nombre"],
                    imagen_url=product.get("imagen_url"),
                    cantidad=item.cantidad,
                    precio_regular=regular,
                    descuento_porcentaje=discount,
                    precio_final=final,
                    subtotal=round(final * item.cantidad, 2),
                    ahorro=round((regular - final) * item.cantidad, 2),
                    stock_disponible=available + item.cantidad_reservada,
                )
            )
        response_items.sort(key=lambda item: item.descuento_porcentaje <= 0)
        offers = [item for item in response_items if item.descuento_porcentaje > 0]
        regulars = [item for item in response_items if item.descuento_porcentaje <= 0]
        subtotal = round(sum(item.subtotal for item in response_items), 2)
        savings = round(sum(item.ahorro for item in response_items), 2)
        return CarritoResponse(
            items_oferta=offers,
            items_regulares=regulars,
            subtotal=subtotal,
            ahorro_total=savings,
            total=round(subtotal, 2),
            reserva_expira_en=cart.reserva_expira_en,
        )
