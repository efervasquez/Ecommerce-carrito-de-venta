"""Logica de negocio de reclamos, reposiciones y logistica inversa (HU-09)."""

import logging
import os
import re
import uuid
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from src.config import get_settings
from src.core.broker import publish_event
from src.modules.auth.models import utcnow
from src.modules.catalogo.repository import (
    CatalogReadRepository,
    CatalogUnavailableError,
    ProductNotFoundError,
)
from src.modules.carrito.inventory import (
    LocalMySQLInventoryProvider,
    StockInsufficientError,
)
from src.modules.carrito.models import InventarioStock
from src.modules.despacho.models import PedidoEstadoHistorial
from src.modules.pagos.models import Pedido, PedidoItem
from src.modules.reclamos.auth import Principal
from src.modules.reclamos.models import MermaAveriada, Reclamo
from src.modules.reclamos.schemas import (
    InspeccionInput,
    InspeccionResponse,
    ReclamoItem,
    ReclamoListadoItem,
    ReclamoRegistroResponse,
)

logger = logging.getLogger(__name__)

ESTADO_APROBADO = "aprobado"
ESTADO_REINTENTO = "reintento_pendiente"
ESTADO_CERRADO = "cerrado_exitoso"
ESTADO_ESCALADO = "escalado_supervision"
ESTADOS_FINALES = {ESTADO_CERRADO, ESTADO_ESCALADO}
MAX_INTENTOS_ADICIONALES = 3
PREFIJO_REPOSICION = "BL-REP-"
QUEUE_DESPACHO = "despacho.organizar"

UPLOADS_DIR = Path(os.getcwd()) / "uploads" / "reclamos"

MSG_FALTA_FOTO_PRODUCTO = "La fotografía del producto dañado es obligatoria."
MSG_FALTA_FOTO_COMPROBANTE = (
    "La fotografía o archivo del comprobante de pago es obligatoria."
)
MSG_FORMATO = "Formato de archivo no soportado. Debe ser JPG, PNG o PDF."
MSG_NO_ENTREGADO = (
    "Solo se pueden registrar reclamos para pedidos con estado Entregado."
)
MSG_PEDIDO_NO_ENCONTRADO = (
    "Pedido no encontrado o no pertenece al usuario autenticado."
)
MSG_PRODUCTO_AJENO = (
    "El producto indicado no pertenece a los ítems del pedido original."
)
MSG_ARREPENTIMIENTO = (
    "No proceden reclamos por arrepentimiento o error en la compra. "
    "Solo aplica para productos dañados o en mal estado."
)
MSG_STOCK = "No hay stock suficiente para generar la reposición."
MSG_RECLAMO_NO_ENCONTRADO = "Reclamo no encontrado."
MSG_FINAL = "El reclamo ya no admite inspecciones en campo (estado final alcanzado)."
MSG_CONFORME_INCOMPLETO = (
    "Para dar conformidad se deben validar físicamente los 3 requisitos: "
    "comprobante original, pertenencia a Botica la Luz y defecto físico."
)
MSG_FALLA_SIN_MOTIVO = (
    "El motivo de la falla es requerido cuando la inspección no es conforme."
)
MSG_CONFORME = "Cambio físico completado con éxito."
MSG_REINTENTO = (
    "Intento fallido registrado. Se permite reprogramar nuevo intento de cambio."
)
MSG_ESCALADO = (
    "Límite de 3 intentos adicionales alcanzado. Reclamo escalado a supervisión."
)

MSG_REEMBOLSO_POLITICA = (
    "Política estricta de cero reembolsos: la botica no realiza devoluciones "
    "de dinero ni extornos."
)
MSG_REEMBOLSO_ACCION = (
    "Acción no permitida: política estricta de reposición física sin "
    "reembolso monetario."
)

_EXT_PRODUCTO = {".jpg", ".jpeg", ".png"}
_EXT_COMPROBANTE = {".jpg", ".jpeg", ".png", ".pdf"}
_MIME_POR_EXT = {
    ".jpg": {"image/jpeg", "image/jpg"},
    ".jpeg": {"image/jpeg", "image/jpg"},
    ".png": {"image/png", "image/x-png"},
    ".pdf": {"application/pdf", "application/x-pdf"},
}
_MIME_GENERICOS = {"", "application/octet-stream", "binary/octet-stream"}

_TERMINOS_ARREPENTIMIENTO = (
    "arrepentimiento",
    "arrepentido",
    "arrepentida",
    "me arrepenti",
    "error de compra",
    "error en la compra",
    "error al comprar",
    "compre por error",
    "compra equivocada",
    "equivocacion",
    "me equivoque",
    "no lo quiero",
    "no la quiero",
    "no lo necesito",
    "no la necesito",
    "ya no lo necesito",
    "ya no la necesito",
    "cambio de opinion",
    "cambie de opinion",
)


def _normalizar(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value.lower()).strip()


def es_arrepentimiento(motivo: str, descripcion: Optional[str]) -> bool:
    texto = _normalizar(f"{motivo or ''} {descripcion or ''}")
    return any(termino in texto for termino in _TERMINOS_ARREPENTIMIENTO)


class ReclamoService:
    """Registro, consulta e inspeccion en campo de reclamos."""

    def __init__(
        self,
        inventory: Optional[LocalMySQLInventoryProvider] = None,
        catalog: Optional[CatalogReadRepository] = None,
    ) -> None:
        self.inventory = inventory or LocalMySQLInventoryProvider()
        self.catalog = catalog or CatalogReadRepository()

    async def registrar(
        self,
        session: AsyncSession,
        principal: Principal,
        *,
        pedido_numero: str,
        producto_id: int,
        motivo: str,
        descripcion: Optional[str],
        foto_producto: Optional[UploadFile],
        foto_comprobante: Optional[UploadFile],
    ) -> ReclamoRegistroResponse:
        if foto_producto is None or not foto_producto.filename:
            raise HTTPException(status_code=422, detail=MSG_FALTA_FOTO_PRODUCTO)
        if foto_comprobante is None or not foto_comprobante.filename:
            raise HTTPException(status_code=422, detail=MSG_FALTA_FOTO_COMPROBANTE)

        self._validar_archivo(foto_producto, _EXT_PRODUCTO)
        self._validar_archivo(foto_comprobante, _EXT_COMPROBANTE)

        if es_arrepentimiento(motivo, descripcion):
            raise HTTPException(status_code=422, detail=MSG_ARREPENTIMIENTO)

        pedido = await session.scalar(
            select(Pedido)
            .where(
                Pedido.numero == pedido_numero,
                Pedido.usuario_id == principal.usuario_id,
            )
            .with_for_update()
        )
        if pedido is None:
            raise HTTPException(status_code=404, detail=MSG_PEDIDO_NO_ENCONTRADO)
        if pedido.estado != "Entregado":
            raise HTTPException(status_code=409, detail=MSG_NO_ENTREGADO)

        item = await session.scalar(
            select(PedidoItem).where(
                PedidoItem.pedido_id == pedido.id,
                PedidoItem.producto_id == producto_id,
            )
        )
        if item is None:
            raise HTTPException(status_code=422, detail=MSG_PRODUCTO_AJENO)

        nombre, stock_inicial = await self._datos_producto(
            producto_id, item.nombre
        )
        await self._descontar_stock(session, producto_id, stock_inicial)

        foto_producto_path = await self._guardar_archivo(foto_producto)
        foto_comprobante_path = await self._guardar_archivo(foto_comprobante)

        ahora = utcnow()
        reclamo = Reclamo(
            pedido_origen_id=pedido.id,
            pedido_reposicion_id=None,
            producto_id=producto_id,
            motivo=motivo,
            descripcion=descripcion,
            foto_producto_url="",
            foto_comprobante_url="",
            foto_producto_path=str(foto_producto_path),
            foto_comprobante_path=str(foto_comprobante_path),
            estado=ESTADO_APROBADO,
            intentos_adicionales_realizados=0,
            creado_en=ahora,
            actualizado_en=ahora,
        )
        session.add(reclamo)
        await session.flush()

        reclamo.foto_producto_url = (
            f"/api/v1/reclamos/{reclamo.id}/evidencias/producto"
        )
        reclamo.foto_comprobante_url = (
            f"/api/v1/reclamos/{reclamo.id}/evidencias/comprobante"
        )

        numero_reposicion = f"{PREFIJO_REPOSICION}{pedido.numero}"
        ya_existe = await session.scalar(
            select(Pedido.id).where(Pedido.numero == numero_reposicion)
        )
        if ya_existe is not None:
            numero_reposicion = f"{numero_reposicion}-{reclamo.id}"

        reposicion = Pedido(
            numero=numero_reposicion,
            usuario_id=pedido.usuario_id,
            carrito_id=pedido.carrito_id,
            direccion_id=pedido.direccion_id,
            zona_id=pedido.zona_id,
            metodo_entrega="delivery",
            tipo="reposicion",
            estado="Registrado",
            monto=0.00,
            moneda="PEN",
            creado_en=ahora,
        )
        session.add(reposicion)
        await session.flush()

        session.add(
            PedidoItem(
                pedido_id=reposicion.id,
                producto_id=producto_id,
                nombre=nombre,
                cantidad=1,
                precio_unitario=0.00,
                subtotal=0.00,
            )
        )
        await session.execute(
            text("UPDATE pedidos SET reclamo_id = :reclamo_id WHERE id = :pedido_id"),
            {"reclamo_id": reclamo.id, "pedido_id": reposicion.id},
        )
        reclamo.pedido_reposicion_id = reposicion.id
        await session.commit()

        await self._publicar_organizar(
            reposicion.numero, int(reposicion.zona_id)
        )

        return ReclamoRegistroResponse(
            id=reclamo.id,
            pedido_origen_numero=pedido.numero,
            pedido_reposicion_numero=reposicion.numero,
            producto_id=producto_id,
            estado=reclamo.estado,
            intentos_adicionales_realizados=reclamo.intentos_adicionales_realizados,
            creado_en=reclamo.creado_en,
        )

    async def listar(
        self,
        session: AsyncSession,
        principal: Principal,
        *,
        estado: Optional[str] = None,
        pedido_numero: Optional[str] = None,
    ) -> list[ReclamoListadoItem]:
        origen = aliased(Pedido)
        reposicion = aliased(Pedido)
        stmt = (
            select(Reclamo, origen.numero, reposicion.numero)
            .join(origen, Reclamo.pedido_origen_id == origen.id)
            .outerjoin(reposicion, Reclamo.pedido_reposicion_id == reposicion.id)
        )
        if principal.rol == "cliente":
            stmt = stmt.where(origen.usuario_id == principal.usuario_id)
        elif principal.rol == "motorizado":
            # v2: la visibilidad del motorizado se hereda de la asignacion del
            # pedido de reposicion BL-REP-... (HU-08).
            stmt = stmt.where(reposicion.motorizado_id == principal.usuario_id)
        if estado:
            stmt = stmt.where(Reclamo.estado == estado)
        if pedido_numero:
            stmt = stmt.where(origen.numero == pedido_numero)
        stmt = stmt.order_by(Reclamo.creado_en.desc(), Reclamo.id.desc())

        rows = (await session.execute(stmt)).all()
        return [
            self._item_listado(reclamo, numero_origen, numero_repo)
            for reclamo, numero_origen, numero_repo in rows
        ]

    async def obtener(
        self, session: AsyncSession, principal: Principal, reclamo_id: int
    ) -> ReclamoItem:
        reclamo = await session.get(Reclamo, reclamo_id)
        if reclamo is None:
            raise HTTPException(status_code=404, detail=MSG_RECLAMO_NO_ENCONTRADO)

        origen = await session.get(Pedido, reclamo.pedido_origen_id)
        reposicion = (
            await session.get(Pedido, reclamo.pedido_reposicion_id)
            if reclamo.pedido_reposicion_id is not None
            else None
        )
        if origen is None:
            raise HTTPException(status_code=404, detail=MSG_RECLAMO_NO_ENCONTRADO)

        if principal.rol == "cliente":
            if int(origen.usuario_id) != principal.usuario_id:
                raise HTTPException(status_code=404, detail=MSG_RECLAMO_NO_ENCONTRADO)
        elif principal.rol == "motorizado":
            asignado = (
                reposicion is not None
                and reposicion.motorizado_id is not None
                and int(reposicion.motorizado_id) == principal.usuario_id
            )
            if not asignado:
                raise HTTPException(
                    status_code=403,
                    detail="No tienes permisos para realizar esta operación.",
                )

        return self._item(
            reclamo,
            origen.numero,
            reposicion.numero if reposicion is not None else None,
            reposicion.estado if reposicion is not None else None,
        )

    async def inspeccionar(
        self,
        session: AsyncSession,
        principal: Principal,
        reclamo_id: int,
        payload: InspeccionInput,
    ) -> InspeccionResponse:
        reclamo = await session.get(Reclamo, reclamo_id, with_for_update=True)
        if reclamo is None:
            raise HTTPException(status_code=404, detail=MSG_RECLAMO_NO_ENCONTRADO)
        if reclamo.estado in ESTADOS_FINALES:
            raise HTTPException(status_code=409, detail=MSG_FINAL)

        ahora = utcnow()
        if payload.resultado == "conforme":
            if not (
                payload.comprobante_verificado
                and payload.pertenencia_botica_verificada
                and payload.defecto_fisico_verificado
            ):
                raise HTTPException(
                    status_code=422, detail=MSG_CONFORME_INCOMPLETO
                )

            reclamo.comprobante_verificado = True
            reclamo.pertenencia_botica_verificada = True
            reclamo.defecto_fisico_verificado = True
            reclamo.estado = ESTADO_CERRADO
            reclamo.actualizado_en = ahora

            if reclamo.pedido_reposicion_id is not None:
                reposicion = await session.get(
                    Pedido, reclamo.pedido_reposicion_id, with_for_update=True
                )
                if reposicion is not None:
                    anterior = reposicion.estado
                    reposicion.estado = "Entregado"
                    session.add(
                        PedidoEstadoHistorial(
                            pedido_id=reposicion.id,
                            estado_anterior=anterior,
                            estado_nuevo="Entregado",
                            usuario_id=principal.usuario_id,
                            creado_en=ahora,
                        )
                    )

            session.add(
                MermaAveriada(
                    reclamo_id=reclamo.id,
                    pedido_id=reclamo.pedido_origen_id,
                    producto_id=reclamo.producto_id,
                    cantidad=1,
                    motivo="Producto recogido en campo",
                    creado_en=ahora,
                )
            )
            await session.commit()
            return InspeccionResponse(
                id=reclamo.id, estado=reclamo.estado, mensaje=MSG_CONFORME
            )

        motivo_falla = (payload.motivo_falla or "").strip()
        if not motivo_falla:
            raise HTTPException(status_code=422, detail=MSG_FALLA_SIN_MOTIVO)

        reclamo.comprobante_verificado = payload.comprobante_verificado
        reclamo.pertenencia_botica_verificada = (
            payload.pertenencia_botica_verificada
        )
        reclamo.defecto_fisico_verificado = payload.defecto_fisico_verificado
        reclamo.motivo_falla = motivo_falla
        reclamo.observaciones = payload.observaciones
        reclamo.intentos_adicionales_realizados += 1
        reclamo.actualizado_en = ahora

        intentos = reclamo.intentos_adicionales_realizados
        if intentos >= MAX_INTENTOS_ADICIONALES:
            reclamo.estado = ESTADO_ESCALADO
            await self._devolver_stock(session, int(reclamo.producto_id))
            if reclamo.pedido_reposicion_id is not None:
                reposicion = await session.get(
                    Pedido, reclamo.pedido_reposicion_id, with_for_update=True
                )
                if reposicion is not None:
                    reposicion.estado = ESTADO_ESCALADO
            await session.commit()
            return InspeccionResponse(
                id=reclamo.id,
                estado=reclamo.estado,
                intentos_adicionales_realizados=intentos,
                intentos_restantes=0,
                mensaje=MSG_ESCALADO,
            )

        reclamo.estado = ESTADO_REINTENTO
        await session.commit()
        return InspeccionResponse(
            id=reclamo.id,
            estado=reclamo.estado,
            intentos_adicionales_realizados=intentos,
            intentos_restantes=MAX_INTENTOS_ADICIONALES - intentos,
            mensaje=MSG_REINTENTO,
        )

    async def _datos_producto(
        self, producto_id: int, nombre_pedido: str
    ) -> tuple[str, int]:
        try:
            producto = await self.catalog.get_by_id(producto_id)
        except (ProductNotFoundError, CatalogUnavailableError):
            return nombre_pedido, 0
        nombre = str(producto.get("nombre") or nombre_pedido)
        return nombre, int(producto.get("stock_disponible") or 0)

    async def _descontar_stock(
        self, session: AsyncSession, producto_id: int, stock_inicial: int
    ) -> None:
        try:
            await self.inventory.reserve_stock_batch(
                session, [(producto_id, 1, stock_inicial)]
            )
            conforme = await self.inventory.confirm_deduction_batch(
                session, [(producto_id, 1)]
            )
        except StockInsufficientError as exc:
            await session.rollback()
            raise HTTPException(status_code=409, detail=MSG_STOCK) from exc
        if not conforme:
            await session.rollback()
            raise HTTPException(status_code=409, detail=MSG_STOCK)

    async def _devolver_stock(
        self, session: AsyncSession, producto_id: int
    ) -> None:
        row = (
            await session.execute(
                select(InventarioStock)
                .where(InventarioStock.producto_id == producto_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if row is None:
            session.add(
                InventarioStock(
                    producto_id=producto_id,
                    disponible=1,
                    reservado=0,
                    actualizado_en=utcnow(),
                )
            )
            return
        row.disponible += 1
        row.actualizado_en = utcnow()

    def _validar_archivo(self, archivo: UploadFile, permitidos: set[str]) -> None:
        extension = Path(archivo.filename or "").suffix.lower()
        if extension not in permitidos:
            raise HTTPException(status_code=422, detail=MSG_FORMATO)
        mime = (archivo.content_type or "").lower()
        if mime in _MIME_GENERICOS:
            return
        if mime not in _MIME_POR_EXT.get(extension, set()):
            raise HTTPException(status_code=422, detail=MSG_FORMATO)

    async def _guardar_archivo(self, archivo: UploadFile) -> Path:
        extension = Path(archivo.filename or "").suffix.lower()
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        destino = UPLOADS_DIR / f"{uuid.uuid4().hex}{extension}"
        contenido = await archivo.read()
        destino.write_bytes(contenido)
        return destino

    @staticmethod
    def _item_listado(
        reclamo: Reclamo, numero_origen: str, numero_reposicion: Optional[str]
    ) -> ReclamoListadoItem:
        return ReclamoListadoItem(
            id=reclamo.id,
            pedido_origen_numero=numero_origen,
            pedido_reposicion_numero=numero_reposicion or "",
            producto_id=reclamo.producto_id,
            estado=reclamo.estado,
            intentos_adicionales_realizados=reclamo.intentos_adicionales_realizados,
            creado_en=reclamo.creado_en,
        )

    @staticmethod
    def _item(
        reclamo: Reclamo,
        numero_origen: str,
        numero_reposicion: Optional[str],
        estado_reposicion: Optional[str],
    ) -> ReclamoItem:
        restantes = max(
            0, MAX_INTENTOS_ADICIONALES - reclamo.intentos_adicionales_realizados
        )
        if reclamo.estado in ESTADOS_FINALES:
            restantes = 0
        return ReclamoItem(
            id=reclamo.id,
            pedido_origen_numero=numero_origen,
            pedido_reposicion_numero=numero_reposicion,
            pedido_reposicion_estado=estado_reposicion,
            producto_id=reclamo.producto_id,
            motivo=reclamo.motivo,
            descripcion=reclamo.descripcion,
            estado=reclamo.estado,
            intentos_adicionales_realizados=reclamo.intentos_adicionales_realizados,
            intentos_restantes=restantes,
            foto_producto_url=reclamo.foto_producto_url,
            foto_comprobante_url=reclamo.foto_comprobante_url,
            comprobante_verificado=reclamo.comprobante_verificado,
            pertenencia_botica_verificada=reclamo.pertenencia_botica_verificada,
            defecto_fisico_verificado=reclamo.defecto_fisico_verificado,
            motivo_falla=reclamo.motivo_falla,
            observaciones=reclamo.observaciones,
            creado_en=reclamo.creado_en,
            actualizado_en=reclamo.actualizado_en,
        )

    async def _publicar_organizar(self, numero: str, zona_id: int) -> None:
        if self._test_mode():
            return
        payload = {
            "type": QUEUE_DESPACHO,
            "evento": QUEUE_DESPACHO,
            "pedido_numeros": [numero],
            "zona_id": zona_id,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        try:
            await publish_event(QUEUE_DESPACHO, payload, timeout=1.0)
        except Exception as exc:  # best-effort: nunca bloquea la operacion
            logger.warning(
                "No se pudo publicar evento despacho.organizar del pedido %s: %s",
                numero,
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
