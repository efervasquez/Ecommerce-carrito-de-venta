"""Logica del backoffice de inventario y contingencia (HU-10)."""

import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.models import utcnow
from src.modules.carrito.models import InventarioStock
from src.modules.inventario.auth import Principal
from src.modules.inventario.models import InventarioAjuste, Producto
from src.modules.inventario.schemas import (
    ProductoCreateInput,
    ProductoDetalle,
    ProductoListadoItem,
    ProductoListadoResponse,
    ProductoUpdateInput,
    StockAjusteInput,
    StockAjusteResponse,
)

MSG_STOCK = (
    "La cantidad de existencias debe ser un número entero mayor o igual a cero."
)
MSG_PRECIO = "El precio regular debe ser mayor a cero."
MSG_DESCUENTO = "El porcentaje de descuento debe estar entre 0 y 100."
MSG_METODOS = "Los métodos de entrega permitidos son delivery y retiro."
MSG_PRODUCTO_NO_ENCONTRADO = "Producto no encontrado."

logger = logging.getLogger(__name__)

METODOS_PERMITIDOS = ("delivery", "retiro")
METODOS_DEFAULT = ["delivery", "retiro"]


class InventarioService:
    """CRUD de productos y ajuste manual de existencias."""

    async def listar(
        self,
        session: AsyncSession,
        *,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ProductoListadoResponse:
        filtros = []
        termino = (q or "").strip()
        if termino:
            patron = f"%{termino.lower()}%"
            filtros.append(
                or_(
                    func.lower(Producto.nombre).like(patron),
                    func.lower(Producto.componentes).like(patron),
                )
            )

        total = int(
            await session.scalar(
                select(func.count(Producto.id)).where(*filtros)
            )
            or 0
        )
        filas = (
            await session.execute(
                select(Producto, InventarioStock)
                .outerjoin(
                    InventarioStock,
                    InventarioStock.producto_id == Producto.id,
                )
                .where(*filtros)
                .order_by(Producto.id.asc())
                .limit(limit)
                .offset(offset)
            )
        ).all()

        items = [
            ProductoListadoItem(
                id=producto.id,
                nombre=producto.nombre,
                componentes=producto.componentes,
                precio_regular=float(producto.precio_regular),
                descuento_porcentaje=float(producto.descuento_porcentaje),
                stock_disponible=stock.disponible if stock is not None else 0,
                stock_reservado=stock.reservado if stock is not None else 0,
                precios_bajos=bool(producto.precios_bajos),
                requiere_receta=bool(producto.requiere_receta),
            )
            for producto, stock in filas
        ]
        return ProductoListadoResponse(items=items, total=total)

    async def detalle(
        self, session: AsyncSession, producto_id: int
    ) -> ProductoDetalle:
        producto = await session.get(Producto, producto_id)
        if producto is None:
            raise HTTPException(status_code=404, detail=MSG_PRODUCTO_NO_ENCONTRADO)
        stock = await self._stock(session, producto_id)
        return self._detalle(producto, stock)

    async def crear(
        self,
        session: AsyncSession,
        principal: Principal,
        payload: ProductoCreateInput,
    ) -> ProductoDetalle:
        precio = self._validar_precio(payload.precio_regular)
        stock_inicial = self._validar_stock(payload.stock_disponible)
        descuento = self._validar_descuento(payload.descuento_porcentaje)
        metodos = self._validar_metodos(payload.metodos_entrega)

        ahora = utcnow()
        producto = Producto(
            nombre=payload.nombre,
            componentes=payload.componentes,
            precio_regular=precio,
            moneda=payload.moneda or "PEN",
            descuento_porcentaje=descuento,
            precios_bajos=bool(payload.precios_bajos),
            requiere_receta=bool(payload.requiere_receta),
            presentacion=payload.presentacion,
            detalle=payload.detalle,
            imagen_url=payload.imagen_url,
            metodos_entrega=metodos,
            contraindicaciones=payload.contraindicaciones or "",
            precauciones_advertencias=payload.precauciones_advertencias or "",
            reacciones_adversas=payload.reacciones_adversas or "",
            creado_en=ahora,
            actualizado_en=ahora,
        )
        session.add(producto)
        await session.flush()

        stock = InventarioStock(
            producto_id=producto.id,
            disponible=stock_inicial,
            reservado=0,
            actualizado_en=ahora,
        )
        session.add(stock)
        await session.commit()
        logger.info(
            "Producto creado en contingencia",
            extra={
                "producto_id": producto.id,
                "usuario_id": principal.usuario_id,
                "stock_inicial": stock_inicial,
            },
        )
        return self._detalle(producto, stock)

    async def actualizar(
        self,
        session: AsyncSession,
        principal: Principal,
        producto_id: int,
        payload: ProductoUpdateInput,
    ) -> ProductoDetalle:
        producto = await session.get(Producto, producto_id, with_for_update=True)
        if producto is None:
            raise HTTPException(status_code=404, detail=MSG_PRODUCTO_NO_ENCONTRADO)

        precio = self._validar_precio(payload.precio_regular)
        if payload.descuento_porcentaje is not None:
            producto.descuento_porcentaje = self._validar_descuento(
                payload.descuento_porcentaje
            )
        if payload.metodos_entrega is not None:
            producto.metodos_entrega = self._validar_metodos(
                payload.metodos_entrega
            )
        if payload.moneda is not None:
            producto.moneda = payload.moneda or "PEN"
        if payload.precios_bajos is not None:
            producto.precios_bajos = bool(payload.precios_bajos)
        if payload.requiere_receta is not None:
            producto.requiere_receta = bool(payload.requiere_receta)
        if payload.imagen_url is not None:
            producto.imagen_url = payload.imagen_url
        if payload.contraindicaciones is not None:
            producto.contraindicaciones = payload.contraindicaciones
        if payload.precauciones_advertencias is not None:
            producto.precauciones_advertencias = payload.precauciones_advertencias
        if payload.reacciones_adversas is not None:
            producto.reacciones_adversas = payload.reacciones_adversas

        producto.nombre = payload.nombre
        producto.componentes = payload.componentes
        producto.precio_regular = precio
        producto.presentacion = payload.presentacion
        producto.detalle = payload.detalle
        producto.actualizado_en = utcnow()
        await session.commit()
        logger.info(
            "Producto actualizado en contingencia",
            extra={
                "producto_id": producto_id,
                "usuario_id": principal.usuario_id,
            },
        )

        stock = await self._stock(session, producto_id)
        return self._detalle(producto, stock)

    async def ajustar_stock(
        self,
        session: AsyncSession,
        principal: Principal,
        producto_id: int,
        payload: StockAjusteInput,
    ) -> StockAjusteResponse:
        producto = await session.get(Producto, producto_id)
        if producto is None:
            raise HTTPException(status_code=404, detail=MSG_PRODUCTO_NO_ENCONTRADO)

        nuevo = self._validar_stock(payload.stock_disponible)
        ahora = utcnow()
        stock = (
            await session.execute(
                select(InventarioStock)
                .where(InventarioStock.producto_id == producto_id)
                .with_for_update()
            )
        ).scalar_one_or_none()

        if stock is None:
            anterior = 0
            stock = InventarioStock(
                producto_id=producto_id,
                disponible=nuevo,
                reservado=0,
                actualizado_en=ahora,
            )
            session.add(stock)
        else:
            anterior = stock.disponible
            stock.disponible = nuevo
            stock.actualizado_en = ahora

        session.add(
            InventarioAjuste(
                producto_id=producto_id,
                usuario_id=principal.usuario_id,
                stock_anterior=anterior,
                stock_nuevo=nuevo,
                motivo=payload.motivo,
                creado_en=ahora,
            )
        )
        await session.commit()
        logger.info(
            "Ajuste manual de stock",
            extra={
                "producto_id": producto_id,
                "usuario_id": principal.usuario_id,
                "stock_anterior": anterior,
                "stock_nuevo": nuevo,
                "motivo": payload.motivo,
            },
        )

        return StockAjusteResponse(
            id=stock.id,
            producto_id=producto_id,
            disponible=stock.disponible,
            reservado=stock.reservado,
            actualizado_en=stock.actualizado_en,
        )

    async def _stock(
        self, session: AsyncSession, producto_id: int
    ) -> Optional[InventarioStock]:
        return await session.scalar(
            select(InventarioStock).where(
                InventarioStock.producto_id == producto_id
            )
        )

    @staticmethod
    def _detalle(
        producto: Producto, stock: Optional[InventarioStock]
    ) -> ProductoDetalle:
        return ProductoDetalle(
            id=producto.id,
            nombre=producto.nombre,
            componentes=producto.componentes,
            precio_regular=float(producto.precio_regular),
            moneda=producto.moneda,
            descuento_porcentaje=float(producto.descuento_porcentaje),
            precios_bajos=bool(producto.precios_bajos),
            requiere_receta=bool(producto.requiere_receta),
            presentacion=producto.presentacion,
            detalle=producto.detalle,
            imagen_url=producto.imagen_url,
            metodos_entrega=list(producto.metodos_entrega or []),
            contraindicaciones=producto.contraindicaciones,
            precauciones_advertencias=producto.precauciones_advertencias,
            reacciones_adversas=producto.reacciones_adversas,
            stock_disponible=stock.disponible if stock is not None else 0,
            stock_reservado=stock.reservado if stock is not None else 0,
            creado_en=producto.creado_en,
            actualizado_en=producto.actualizado_en,
        )

    @staticmethod
    def _validar_stock(value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise HTTPException(status_code=422, detail=MSG_STOCK)
        return int(value)

    @staticmethod
    def _validar_precio(value: object) -> float:
        if isinstance(value, bool):
            raise HTTPException(status_code=422, detail=MSG_PRECIO)
        try:
            precio = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=MSG_PRECIO) from exc
        if precio <= 0:
            raise HTTPException(status_code=422, detail=MSG_PRECIO)
        return round(precio, 2)

    @staticmethod
    def _validar_descuento(value: object) -> float:
        if value is None:
            return 0.0
        if isinstance(value, bool):
            raise HTTPException(status_code=422, detail=MSG_DESCUENTO)
        try:
            descuento = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=MSG_DESCUENTO) from exc
        if descuento < 0 or descuento > 100:
            raise HTTPException(status_code=422, detail=MSG_DESCUENTO)
        return round(descuento, 2)

    @staticmethod
    def _validar_metodos(value: Optional[list[str]]) -> list[str]:
        if value is None:
            return list(METODOS_DEFAULT)
        if not isinstance(value, list) or not value:
            raise HTTPException(status_code=422, detail=MSG_METODOS)
        resultado: list[str] = []
        for metodo in value:
            if metodo not in METODOS_PERMITIDOS:
                raise HTTPException(status_code=422, detail=MSG_METODOS)
            if metodo not in resultado:
                resultado.append(metodo)
        return resultado
