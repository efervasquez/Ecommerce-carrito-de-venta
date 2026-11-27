"""Consultas agregadas de solo lectura para la reporteria (HU-11)."""

import logging
import re
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.carrito.models import InventarioStock
from src.modules.inventario.models import Producto
from src.modules.pagos.models import Pedido, PedidoItem
from src.modules.reportes.auth import Principal
from src.modules.reportes.schemas import (
    InventarioCritico,
    PedidoBalance,
    ProductoRotacion,
    ProductoStockCritico,
    VentasReporte,
)

logger = logging.getLogger(__name__)

ESTADOS_CICLO = ("Registrado", "Preparando producto", "En camino", "Entregado")
UMBRAL_STOCK_BAJO = 6
MONEDA = "PEN"

MSG_FORMATO_FECHA = "El formato de fecha debe ser YYYY-MM-DD."
MSG_RANGO_FECHAS = "La fecha de fin no puede ser anterior a la fecha de inicio."

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ReportesService:
    """Agregaciones de ventas, balance de pedidos e inventario critico."""

    async def ventas(
        self,
        session: AsyncSession,
        principal: Principal,
        fecha_inicio: Optional[str],
        fecha_fin: Optional[str],
    ) -> VentasReporte:
        inicio, fin = self._rango(fecha_inicio, fecha_fin)
        desde = datetime.combine(inicio, datetime.min.time())
        hasta = datetime.combine(fin + timedelta(days=1), datetime.min.time())
        filtros = [
            Pedido.tipo != "reposicion",
            Pedido.creado_en >= desde,
            Pedido.creado_en < hasta,
        ]

        total_ordenes = int(
            await session.scalar(
                select(func.count(Pedido.id)).where(*filtros)
            )
            or 0
        )
        monto = await session.scalar(
            select(func.coalesce(func.sum(Pedido.monto), 0)).where(*filtros)
        )
        unidades = await session.scalar(
            select(func.coalesce(func.sum(PedidoItem.cantidad), 0))
            .join(Pedido, PedidoItem.pedido_id == Pedido.id)
            .where(*filtros)
        )

        logger.info(
            "Consulta de reporte de ventas",
            extra={
                "reporte": "ventas",
                "usuario_id": principal.usuario_id,
                "fecha_inicio": inicio.isoformat(),
                "fecha_fin": fin.isoformat(),
            },
        )
        return VentasReporte(
            fecha_inicio=inicio.isoformat(),
            fecha_fin=fin.isoformat(),
            total_ordenes=total_ordenes,
            unidades_vendidas=int(unidades or 0),
            monto_total_facturado=round(float(monto or 0), 2),
            moneda=MONEDA,
        )

    async def balance(
        self, session: AsyncSession, principal: Principal
    ) -> PedidoBalance:
        balance = {estado: 0 for estado in ESTADOS_CICLO}
        filas = await session.execute(
            select(Pedido.estado, func.count(Pedido.id)).group_by(Pedido.estado)
        )
        for estado, total in filas.all():
            if estado in balance:
                balance[estado] = int(total)

        logger.info(
            "Consulta de reporte de pedidos por estado",
            extra={"reporte": "pedidos-balance", "usuario_id": principal.usuario_id},
        )
        return PedidoBalance(
            balance=balance, total_pedidos=sum(balance.values())
        )

    async def inventario_critico(
        self, session: AsyncSession, principal: Principal
    ) -> InventarioCritico:
        disponible = func.coalesce(InventarioStock.disponible, 0)
        base = (
            select(Producto.id, Producto.nombre, disponible.label("stock"))
            .outerjoin(
                InventarioStock,
                InventarioStock.producto_id == Producto.id,
            )
        )

        filas_bajo = (
            await session.execute(
                base.where(disponible < UMBRAL_STOCK_BAJO).order_by(
                    Producto.nombre.asc()
                )
            )
        ).all()
        filas_quiebre = (
            await session.execute(
                base.where(disponible == 0).order_by(Producto.nombre.asc())
            )
        ).all()

        unidades = func.sum(PedidoItem.cantidad).label("unidades")
        filas_rotacion = (
            await session.execute(
                select(
                    PedidoItem.producto_id,
                    Producto.nombre,
                    unidades,
                )
                .join(Pedido, PedidoItem.pedido_id == Pedido.id)
                .outerjoin(Producto, Producto.id == PedidoItem.producto_id)
                .where(Pedido.tipo != "reposicion")
                .group_by(PedidoItem.producto_id, Producto.nombre)
                .having(func.sum(PedidoItem.cantidad) > 0)
                .order_by(unidades.desc(), PedidoItem.producto_id.asc())
            )
        ).all()

        logger.info(
            "Consulta de reporte de inventario critico",
            extra={
                "reporte": "inventario-critico",
                "usuario_id": principal.usuario_id,
            },
        )
        return InventarioCritico(
            stock_bajo=[
                ProductoStockCritico(
                    producto_id=int(producto_id),
                    nombre=nombre,
                    stock_disponible=int(stock),
                )
                for producto_id, nombre, stock in filas_bajo
            ],
            quiebres=[
                ProductoStockCritico(
                    producto_id=int(producto_id),
                    nombre=nombre,
                    stock_disponible=int(stock),
                )
                for producto_id, nombre, stock in filas_quiebre
            ],
            mayor_rotacion=[
                ProductoRotacion(
                    producto_id=int(producto_id),
                    nombre=nombre or f"Producto {producto_id}",
                    unidades_vendidas=int(total),
                )
                for producto_id, nombre, total in filas_rotacion
            ],
        )

    def _rango(
        self, fecha_inicio: Optional[str], fecha_fin: Optional[str]
    ) -> tuple[date, date]:
        hoy = date.today()
        inicio_default = hoy.replace(day=1)

        inicio = (
            self._parse_fecha(fecha_inicio)
            if fecha_inicio is not None
            else inicio_default
        )
        fin = self._parse_fecha(fecha_fin) if fecha_fin is not None else hoy
        if fin < inicio:
            raise HTTPException(status_code=422, detail=MSG_RANGO_FECHAS)
        return inicio, fin

    @staticmethod
    def _parse_fecha(value: str) -> date:
        if not _ISO_DATE.match(value or ""):
            raise HTTPException(status_code=422, detail=MSG_FORMATO_FECHA)
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=MSG_FORMATO_FECHA) from exc
