"""Logica de negocio del buzon de despacho y ciclo de vida de pedidos (HU-08)."""

import logging
import os
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.core.broker import publish_event
from src.modules.auth.models import Usuario, utcnow
from src.modules.despacho.models import PedidoEstadoHistorial
from src.modules.despacho.schemas import (
    AsignacionInput,
    AsignacionResponse,
    EstadoPedidoInput,
    HistorialEstadoItem,
    PedidoDespachoItem,
    ZonaDespachoResumen,
)
from src.modules.pagos.models import Pedido, Zona

logger = logging.getLogger(__name__)

ESTADO_REGISTRADO = "Registrado"
ESTADO_PREPARANDO = "Preparando producto"
ESTADO_EN_CAMINO = "En camino"
ESTADO_ENTREGADO = "Entregado"
ESTADO_INCIDENCIA = "incidencia_stock"

TRANSICIONES = {
    ESTADO_PREPARANDO: ESTADO_EN_CAMINO,
    ESTADO_EN_CAMINO: ESTADO_ENTREGADO,
}

MSG_TRANSICION_INVALIDA = (
    "Transición de estado inválida: el pedido debe pasar primero por "
    "'Preparando producto' y 'En camino'"
)
MSG_ASIGNACION_INVALIDA = (
    "No se puede asignar: uno o más pedidos no existen, no pertenecen a la zona "
    "o no están en estado Registrado."
)
MSG_MOTORIZADO_INVALIDO = "Motorizado no encontrado."
MSG_PEDIDO_NO_ENCONTRADO = "Pedido no encontrado."
MSG_PEDIDO_NO_DISPONIBLE = "El pedido no está disponible para auto-asignación."
MSG_NO_ASIGNADO = "El pedido no está asignado a tu usuario."
MSG_FIFO = "Debes auto-asignarte el pedido más antiguo de la zona."

QUEUE_DESPACHO = "despacho.organizar"


class DespachoService:
    """Consultas y transiciones del flujo Registrado → Preparando → En camino → Entregado."""

    async def listar_pedidos(
        self,
        session: AsyncSession,
        estado: Optional[str] = None,
        zona_id: Optional[int] = None,
        actor_id: Optional[int] = None,
        rol: Optional[str] = None,
    ) -> list[PedidoDespachoItem]:
        stmt = (
            select(Pedido, Zona.distrito)
            .join(Zona, Pedido.zona_id == Zona.id)
            .order_by(Pedido.creado_en.asc(), Pedido.id.asc())
        )
        if estado:
            stmt = stmt.where(Pedido.estado == estado)
        if zona_id is not None:
            stmt = stmt.where(Pedido.zona_id == zona_id)
        if rol == "motorizado" and actor_id is not None:
            stmt = stmt.where(Pedido.motorizado_id == actor_id)
        rows = (await session.execute(stmt)).all()
        return [self._item(pedido, distrito) for pedido, distrito in rows]

    async def resumen_zonas(self, session: AsyncSession) -> list[ZonaDespachoResumen]:
        zonas = (
            await session.execute(select(Zona).order_by(Zona.id.asc()))
        ).scalars().all()
        counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        filas = await session.execute(
            select(Pedido.zona_id, Pedido.estado, func.count(Pedido.id)).group_by(
                Pedido.zona_id, Pedido.estado
            )
        )
        for zona_id, estado, total in filas.all():
            counts[int(zona_id)][estado] = int(total)

        resumen: list[ZonaDespachoResumen] = []
        for zona in zonas:
            por_estado = counts.get(int(zona.id), {})
            resumen.append(
                ZonaDespachoResumen(
                    zona_id=int(zona.id),
                    nombre=zona.nombre,
                    distrito=zona.distrito,
                    pedidos_registrados=por_estado.get(ESTADO_REGISTRADO, 0),
                    pedidos_preparando=por_estado.get(ESTADO_PREPARANDO, 0),
                    pedidos_en_camino=por_estado.get(ESTADO_EN_CAMINO, 0),
                    pedidos_entregados=por_estado.get(ESTADO_ENTREGADO, 0),
                )
            )
        return resumen

    async def asignar_lote(
        self,
        session: AsyncSession,
        payload: AsignacionInput,
        actor_id: int,
    ) -> AsignacionResponse:
        motorizado = await session.get(Usuario, payload.motorizado_id)
        if motorizado is None or motorizado.rol != "motorizado":
            raise HTTPException(status_code=404, detail=MSG_MOTORIZADO_INVALIDO)

        numeros = list(dict.fromkeys(payload.pedido_numeros))
        pedidos = (
            await session.execute(
                select(Pedido)
                .where(Pedido.numero.in_(numeros))
                .with_for_update()
            )
        ).scalars().all()
        por_numero = {pedido.numero: pedido for pedido in pedidos}

        for numero in numeros:
            pedido = por_numero.get(numero)
            if (
                pedido is None
                or int(pedido.zona_id) != payload.zona_id
                or pedido.estado != ESTADO_REGISTRADO
            ):
                await session.rollback()
                raise HTTPException(status_code=409, detail=MSG_ASIGNACION_INVALIDA)

        ahora = utcnow()
        for numero in numeros:
            pedido = por_numero[numero]
            pedido.estado = ESTADO_PREPARANDO
            pedido.motorizado_id = payload.motorizado_id
            pedido.asignado_en = ahora
            session.add(
                PedidoEstadoHistorial(
                    pedido_id=pedido.id,
                    estado_anterior=ESTADO_REGISTRADO,
                    estado_nuevo=ESTADO_PREPARANDO,
                    usuario_id=actor_id,
                    creado_en=ahora,
                )
            )
        await session.commit()

        await self._publicar_organizar(
            numeros,
            zona_id=payload.zona_id,
            motorizado_id=payload.motorizado_id,
        )
        return AsignacionResponse(
            zona_id=payload.zona_id,
            motorizado_id=payload.motorizado_id,
            asignados=numeros,
        )

    async def pendientes(
        self, session: AsyncSession, zona_id: int
    ) -> list[PedidoDespachoItem]:
        stmt = (
            select(Pedido, Zona.distrito)
            .join(Zona, Pedido.zona_id == Zona.id)
            .where(Pedido.estado == ESTADO_REGISTRADO, Pedido.zona_id == zona_id)
            .order_by(Pedido.creado_en.asc(), Pedido.id.asc())
        )
        rows = (await session.execute(stmt)).all()
        return [self._item(pedido, distrito) for pedido, distrito in rows]

    async def mis_pedidos(
        self, session: AsyncSession, motorizado_id: int
    ) -> list[PedidoDespachoItem]:
        stmt = (
            select(Pedido, Zona.distrito)
            .join(Zona, Pedido.zona_id == Zona.id)
            .where(
                Pedido.motorizado_id == motorizado_id,
                Pedido.estado.in_(
                    [ESTADO_PREPARANDO, ESTADO_EN_CAMINO, ESTADO_ENTREGADO]
                ),
            )
            .order_by(Pedido.creado_en.asc(), Pedido.id.asc())
        )
        rows = (await session.execute(stmt)).all()
        return [self._item(pedido, distrito) for pedido, distrito in rows]

    async def auto_asignar(
        self, session: AsyncSession, numero: str, actor_id: int
    ) -> PedidoDespachoItem:
        pedido = await self._pedido_bloqueado(session, numero)
        if pedido.estado != ESTADO_REGISTRADO:
            await session.rollback()
            raise HTTPException(status_code=409, detail=MSG_PEDIDO_NO_DISPONIBLE)

        mas_antiguo = await session.scalar(
            select(Pedido)
            .where(
                Pedido.zona_id == pedido.zona_id,
                Pedido.estado == ESTADO_REGISTRADO,
            )
            .order_by(Pedido.creado_en.asc(), Pedido.id.asc())
            .limit(1)
        )
        if mas_antiguo is None or int(mas_antiguo.id) != int(pedido.id):
            await session.rollback()
            raise HTTPException(status_code=409, detail=MSG_FIFO)

        ahora = utcnow()
        anterior = pedido.estado
        pedido.estado = ESTADO_PREPARANDO
        pedido.motorizado_id = actor_id
        pedido.asignado_en = ahora
        session.add(
            PedidoEstadoHistorial(
                pedido_id=pedido.id,
                estado_anterior=anterior,
                estado_nuevo=ESTADO_PREPARANDO,
                usuario_id=actor_id,
                creado_en=ahora,
            )
        )
        await session.commit()

        await self._publicar_organizar(
            [pedido.numero],
            zona_id=int(pedido.zona_id),
            motorizado_id=actor_id,
        )
        return await self._item_con_distrito(session, pedido)

    async def avanzar_estado(
        self,
        session: AsyncSession,
        numero: str,
        payload: EstadoPedidoInput,
        actor_id: int,
    ) -> PedidoDespachoItem:
        pedido = await self._pedido_bloqueado(session, numero)

        if pedido.estado == ESTADO_INCIDENCIA:
            await session.rollback()
            raise HTTPException(status_code=409, detail=MSG_TRANSICION_INVALIDA)
        if pedido.motorizado_id is None or int(pedido.motorizado_id) != actor_id:
            await session.rollback()
            raise HTTPException(status_code=403, detail=MSG_NO_ASIGNADO)

        esperado = TRANSICIONES.get(pedido.estado)
        if esperado != payload.estado:
            await session.rollback()
            raise HTTPException(status_code=409, detail=MSG_TRANSICION_INVALIDA)

        ahora = utcnow()
        anterior = pedido.estado
        pedido.estado = payload.estado
        session.add(
            PedidoEstadoHistorial(
                pedido_id=pedido.id,
                estado_anterior=anterior,
                estado_nuevo=payload.estado,
                usuario_id=actor_id,
                creado_en=ahora,
            )
        )
        await session.commit()

        await self._publicar_organizar(
            [pedido.numero],
            zona_id=int(pedido.zona_id),
            motorizado_id=actor_id,
        )
        return await self._item_con_distrito(session, pedido)

    async def historial(
        self, session: AsyncSession, numero: str, actor_id: int, rol: str
    ) -> list[HistorialEstadoItem]:
        pedido = await session.scalar(select(Pedido).where(Pedido.numero == numero))
        if pedido is None:
            raise HTTPException(status_code=404, detail=MSG_PEDIDO_NO_ENCONTRADO)
        if rol == "motorizado" and (
            pedido.motorizado_id is None or int(pedido.motorizado_id) != actor_id
        ):
            raise HTTPException(status_code=403, detail=MSG_NO_ASIGNADO)

        filas = (
            await session.execute(
                select(PedidoEstadoHistorial)
                .where(PedidoEstadoHistorial.pedido_id == pedido.id)
                .order_by(
                    PedidoEstadoHistorial.creado_en.asc(),
                    PedidoEstadoHistorial.id.asc(),
                )
            )
        ).scalars().all()
        return [
            HistorialEstadoItem(
                estado_anterior=fila.estado_anterior,
                estado_nuevo=fila.estado_nuevo,
                usuario_id=fila.usuario_id,
                timestamp=fila.creado_en,
            )
            for fila in filas
        ]

    async def _pedido_bloqueado(self, session: AsyncSession, numero: str) -> Pedido:
        pedido = await session.scalar(
            select(Pedido).where(Pedido.numero == numero).with_for_update()
        )
        if pedido is None:
            raise HTTPException(status_code=404, detail=MSG_PEDIDO_NO_ENCONTRADO)
        return pedido

    async def _item_con_distrito(
        self, session: AsyncSession, pedido: Pedido
    ) -> PedidoDespachoItem:
        zona = await session.get(Zona, pedido.zona_id)
        distrito = zona.distrito if zona is not None else ""
        return self._item(pedido, distrito)

    @staticmethod
    def _item(pedido: Pedido, distrito: str) -> PedidoDespachoItem:
        return PedidoDespachoItem(
            numero=pedido.numero,
            estado=pedido.estado,
            zona_id=int(pedido.zona_id),
            distrito=distrito,
            metodo_entrega=pedido.metodo_entrega,
            motorizado_id=(
                int(pedido.motorizado_id) if pedido.motorizado_id is not None else None
            ),
            monto=float(pedido.monto),
            creado_en=pedido.creado_en,
        )

    async def _publicar_organizar(
        self,
        numeros: list[str],
        *,
        zona_id: int,
        motorizado_id: int,
    ) -> None:
        if self._test_mode():
            return
        payload = {
            "type": QUEUE_DESPACHO,
            "evento": QUEUE_DESPACHO,
            "pedido_numeros": numeros,
            "zona_id": zona_id,
            "motorizado_id": motorizado_id,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        try:
            await publish_event(QUEUE_DESPACHO, payload, timeout=1.0)
        except Exception as exc:  # best-effort: nunca bloquea la operacion
            logger.warning(
                "No se pudo publicar evento despacho.organizar (%s pedidos): %s",
                len(numeros),
                type(exc).__name__,
            )

    @staticmethod
    def _test_mode() -> bool:
        if "PYTEST_CURRENT_TEST" in os.environ:
            return True
        settings = get_settings()
        return settings.app_env.lower() in {"test", "testing"} or os.environ.get(
            "ENVIRONMENT", ""
        ).lower() in {"test", "testing"}
