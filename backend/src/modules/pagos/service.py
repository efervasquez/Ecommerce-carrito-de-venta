"""Orquestacion de entrega, checkout de pago, webhook y consultas (ADR-0013)."""

import logging
import uuid
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.core.broker import publish_event
from src.modules.auth.models import utcnow
from src.modules.carrito.inventory import LocalMySQLInventoryProvider
from src.modules.carrito.models import Carrito, CarritoItem
from src.modules.carrito.schemas import CheckoutResponse
from src.modules.carrito.service import CartActor, CartService
from src.modules.pagos import gateway
from src.modules.pagos.models import Direccion, Pago, Pedido, PedidoItem, Zona
from src.modules.pagos.schemas import (
    CheckoutInput,
    CheckoutPagoResponse,
    DireccionResponse,
    PagoEstadoResponse,
    PedidoResponse,
    ZonaResponse,
)

logger = logging.getLogger(__name__)

EMPTY_CART_MESSAGE = "El carrito está vacío"
ZONA_MESSAGE = "Zona no disponible"
DIRECCION_MESSAGE = "Dirección no disponible"
RESERVA_MESSAGE = "La reserva no está vigente"
STRIPE_ERROR_MESSAGE = "No se pudo iniciar el pago con Stripe."
METODOS_ENTREGA = {"delivery", "retiro"}


class PagoService:
    def __init__(
        self,
        cart_service: Optional[CartService] = None,
        inventory: Optional[LocalMySQLInventoryProvider] = None,
    ) -> None:
        self.cart_service = cart_service or CartService()
        self.inventory = inventory or LocalMySQLInventoryProvider()

    async def listar_zonas(self, session: AsyncSession) -> list[ZonaResponse]:
        result = await session.execute(
            select(Zona).where(Zona.activo.is_(True)).order_by(Zona.id)
        )
        return [
            ZonaResponse(
                id=zona.id,
                nombre=zona.nombre,
                distrito=zona.distrito,
                tiempo_estimado_min=zona.tiempo_estimado_min,
            )
            for zona in result.scalars().all()
        ]

    async def listar_direcciones(
        self, session: AsyncSession, usuario_id: int
    ) -> list[DireccionResponse]:
        result = await session.execute(
            select(Direccion)
            .where(Direccion.usuario_id == usuario_id)
            .order_by(Direccion.id)
        )
        return [
            DireccionResponse(
                id=d.id,
                direccion_linea1=d.direccion_linea1,
                referencia=d.referencia,
                telefono_contacto=d.telefono_contacto,
                zona_id=d.zona_id,
            )
            for d in result.scalars().all()
        ]

    async def crear_direccion(
        self, session: AsyncSession, usuario_id: int, payload
    ) -> DireccionResponse:
        zona = await session.get(Zona, payload.zona_id)
        if zona is None or not zona.activo:
            raise HTTPException(status_code=409, detail=ZONA_MESSAGE)
        direccion = Direccion(
            usuario_id=usuario_id,
            zona_id=zona.id,
            direccion_linea1=payload.direccion_linea1,
            referencia=payload.referencia,
            telefono_contacto=payload.telefono_contacto,
        )
        session.add(direccion)
        await session.commit()
        await session.refresh(direccion)
        return DireccionResponse(
            id=direccion.id,
            direccion_linea1=direccion.direccion_linea1,
            referencia=direccion.referencia,
            telefono_contacto=direccion.telefono_contacto,
            zona_id=direccion.zona_id,
        )

    async def iniciar_checkout(
        self,
        session: AsyncSession,
        actor: CartActor,
        payload: Optional[CheckoutInput],
    ):
        """Guest: reserva 24h sin pago. Autenticado: prorroga + PaymentIntent."""
        if actor.is_guest or actor.user_id is None:
            respuesta = await self.cart_service.checkout_guest(session, actor)
            respuesta.requiere_autenticacion = True
            return respuesta

        carrito_response = await self.cart_service.get_cart(session, actor)
        if not carrito_response.items_oferta and not carrito_response.items_regulares:
            raise HTTPException(status_code=409, detail=EMPTY_CART_MESSAGE)

        metodo = (payload.metodo_entrega if payload else None) or "retiro"
        if metodo not in METODOS_ENTREGA:
            raise HTTPException(
                status_code=422, detail="El campo metodo_entrega es inválido."
            )

        direccion_id: Optional[int] = None
        if metodo == "delivery":
            if payload is None or payload.direccion_id is None:
                raise HTTPException(
                    status_code=409, detail="Se requiere una dirección para delivery."
                )
            direccion = await session.get(Direccion, payload.direccion_id)
            if direccion is None or direccion.usuario_id != actor.user_id:
                raise HTTPException(status_code=404, detail=DIRECCION_MESSAGE)
            zona = await session.get(Zona, direccion.zona_id)
            if zona is None or not zona.activo:
                raise HTTPException(status_code=409, detail=ZONA_MESSAGE)
            direccion_id = direccion.id
            zona_id = zona.id
        else:
            zona = await session.scalar(
                select(Zona).where(Zona.activo.is_(True)).order_by(Zona.id)
            )
            if zona is None:
                raise HTTPException(status_code=409, detail=ZONA_MESSAGE)
            zona_id = zona.id

        cart = await self.cart_service._get_or_create_cart(session, actor)
        if cart.reserva_expira_en is None or cart.reserva_expira_en <= utcnow():
            raise HTTPException(status_code=409, detail=RESERVA_MESSAGE)

        settings = get_settings()
        cart.reserva_expira_en = utcnow() + timedelta(
            seconds=settings.checkout_prorroga_seconds
        )
        cart.estado = "en_pago"

        intento = (
            int(
                await session.scalar(
                    select(func.count(Pago.id)).where(Pago.carrito_id == cart.id)
                )
                or 0
            )
            + 1
        )
        clave = gateway.idempotency_key(cart.id, intento)
        try:
            intent = await gateway.create_payment_intent(
                cart.id, intento, carrito_response.total, "PEN"
            )
        except gateway.StripeGatewayError as exc:
            cart.estado = "activo"
            raise HTTPException(status_code=502, detail=STRIPE_ERROR_MESSAGE) from exc

        pago = Pago(
            payment_intent_id=intent.payment_intent_id,
            idempotencia_key=clave,
            carrito_id=cart.id,
            usuario_id=actor.user_id,
            intento=intento,
            direccion_id=direccion_id,
            zona_id=zona_id,
            metodo_entrega=metodo,
            monto=carrito_response.total,
            moneda="PEN",
            estado="procesando",
        )
        session.add(pago)
        await session.commit()
        return CheckoutPagoResponse(
            payment_intent_id=intent.payment_intent_id,
            client_secret=intent.client_secret,
            monto=carrito_response.total,
            moneda="PEN",
            reserva_expira_en=cart.reserva_expira_en,
        )

    async def procesar_webhook(
        self, session: AsyncSession, event: dict
    ) -> bool:
        """Devuelve True si el evento cambio estado (no idempotente/duplicado)."""
        tipo = event.get("type")
        objeto = (event.get("data") or {}).get("object") or {}
        payment_intent_id = objeto.get("id")
        if not payment_intent_id:
            return False
        if tipo == "payment_intent.succeeded":
            return await self._confirmar_pago(session, str(payment_intent_id))
        if tipo == "payment_intent.payment_failed":
            return await self._rechazar_pago(session, str(payment_intent_id))
        return False

    async def _confirmar_pago(
        self, session: AsyncSession, payment_intent_id: str
    ) -> bool:
        pago = await session.scalar(
            select(Pago)
            .where(Pago.payment_intent_id == payment_intent_id)
            .with_for_update()
        )
        if pago is None or pago.estado != "procesando":
            return False

        cart = await session.get(Carrito, pago.carrito_id, with_for_update=True)
        if cart is None:
            return False
        items = await self.cart_service._get_items(session, cart.id, lock=True)
        reservas = [
            (item.producto_id, item.cantidad_reservada)
            for item in items
            if item.cantidad_reservada > 0
        ]
        conforme = True
        if reservas:
            conforme = await self.inventory.confirm_deduction_batch(session, reservas)
        estado_pedido = "Registrado" if conforme else "incidencia_stock"

        pedido = Pedido(
            numero=f"BL-TEMP-{uuid.uuid4().hex[:16]}",
            usuario_id=pago.usuario_id,
            carrito_id=cart.id,
            direccion_id=pago.direccion_id,
            zona_id=pago.zona_id,
            metodo_entrega=pago.metodo_entrega,
            estado=estado_pedido,
            monto=pago.monto,
            moneda=pago.moneda,
        )
        session.add(pedido)
        await session.flush()
        settings = get_settings()
        pedido.numero = f"BL-{settings.pedido_secuencia_base + int(pedido.id)}"

        for item in items:
            try:
                producto = await self.cart_service._get_product(item.producto_id)
                nombre = producto["nombre"]
            except HTTPException:
                nombre = f"Producto {item.producto_id}"
            session.add(
                PedidoItem(
                    pedido_id=pedido.id,
                    producto_id=item.producto_id,
                    nombre=nombre,
                    cantidad=item.cantidad,
                    precio_unitario=item.precio_unitario,
                    subtotal=round(float(item.precio_unitario) * item.cantidad, 2),
                )
            )

        pago.estado = "confirmado"
        pago.pedido_id = pedido.id
        pago.actualizado_en = utcnow()
        cart.estado = "completado"
        cart.reserva_expira_en = None
        await session.execute(delete(CarritoItem).where(CarritoItem.carrito_id == cart.id))
        await session.commit()

        await self._publicar_eventos(pedido)
        return True

    async def _rechazar_pago(
        self, session: AsyncSession, payment_intent_id: str
    ) -> bool:
        pago = await session.scalar(
            select(Pago)
            .where(Pago.payment_intent_id == payment_intent_id)
            .with_for_update()
        )
        if pago is None or pago.estado != "procesando":
            return False
        cart = await session.get(Carrito, pago.carrito_id, with_for_update=True)
        if cart is not None:
            items = await self.cart_service._get_items(session, cart.id, lock=True)
            reservas = [
                (item.producto_id, item.cantidad_reservada)
                for item in items
                if item.cantidad_reservada > 0
            ]
            if reservas:
                await self.inventory.release_reservation_batch(session, reservas)
            for item in items:
                item.cantidad_reservada = 0
            cart.estado = "activo"
            cart.reserva_expira_en = None
        pago.estado = "rechazado"
        pago.actualizado_en = utcnow()
        await session.commit()
        return True

    async def _publicar_eventos(self, pedido: Pedido) -> None:
        eventos = (
            (
                "email.critico",
                {
                    "type": "pedido.confirmado",
                    "numero": pedido.numero,
                    "pedido_id": pedido.id,
                    "usuario_id": pedido.usuario_id,
                },
            ),
            (
                "despacho.organizar",
                {
                    "type": "despacho.organizar",
                    "numero": pedido.numero,
                    "pedido_id": pedido.id,
                    "zona_id": pedido.zona_id,
                    "metodo_entrega": pedido.metodo_entrega,
                },
            ),
        )
        for cola, payload in eventos:
            try:
                await publish_event(cola, payload, timeout=1.0)
            except Exception as exc:
                logger.warning(
                    "No se pudo publicar evento %s del pedido %s: %s",
                    payload["type"],
                    pedido.numero,
                    type(exc).__name__,
                )

    async def estado_pago(
        self, session: AsyncSession, payment_intent_id: str, usuario_id: int
    ) -> PagoEstadoResponse:
        pago = await session.scalar(
            select(Pago).where(
                Pago.payment_intent_id == payment_intent_id,
                Pago.usuario_id == usuario_id,
            )
        )
        if pago is None:
            raise HTTPException(status_code=404, detail="Pago no encontrado.")
        pedido = None
        if pago.estado == "confirmado" and pago.pedido_id is not None:
            entity = await session.get(Pedido, pago.pedido_id)
            if entity is not None:
                pedido = {
                    "numero": entity.numero,
                    "estado": entity.estado,
                    "monto": float(entity.monto),
                    "moneda": entity.moneda,
                }
        return PagoEstadoResponse(estado=pago.estado, pedido=pedido)

    async def obtener_pedido(
        self, session: AsyncSession, numero: str, usuario_id: int
    ) -> PedidoResponse:
        pedido = await session.scalar(
            select(Pedido).where(
                Pedido.numero == numero, Pedido.usuario_id == usuario_id
            )
        )
        if pedido is None:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")
        result = await session.execute(
            select(PedidoItem)
            .where(PedidoItem.pedido_id == pedido.id)
            .order_by(PedidoItem.id)
        )
        items = [
            {
                "producto_id": item.producto_id,
                "nombre": item.nombre,
                "cantidad": item.cantidad,
                "precio_unitario": float(item.precio_unitario),
                "subtotal": float(item.subtotal),
            }
            for item in result.scalars().all()
        ]
        entrega = "Retiro en botica"
        if pedido.metodo_entrega == "delivery" and pedido.direccion_id is not None:
            direccion = await session.get(Direccion, pedido.direccion_id)
            if direccion is not None:
                entrega = direccion.direccion_linea1
                if direccion.referencia:
                    entrega = f"{entrega} ({direccion.referencia})"
        return PedidoResponse(
            numero=pedido.numero,
            estado=pedido.estado,
            items=items,
            monto=float(pedido.monto),
            moneda=pedido.moneda,
            metodo_entrega=pedido.metodo_entrega,
            entrega=entrega,
        )
