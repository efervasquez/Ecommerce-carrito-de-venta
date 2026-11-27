"""Servicio de jobs OCR: normalizacion, stock atomico y validacion asistida."""

import json
import logging
import uuid
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.core.broker import publish_event
from src.core.database import get_sessionmaker
from src.modules.auth.models import utcnow
from src.modules.carrito.inventory import LocalMySQLInventoryProvider
from src.modules.carrito.models import CarritoItem, Sesion
from src.modules.carrito.service import CartActor, CartService
from src.modules.catalogo.repository import CatalogReadRepository, ProductNotFoundError
from src.modules.ocr.constants import (
    ERROR_MESSAGE,
    LOW_CONFIDENCE_MESSAGE,
    QUEUE_NAME,
    SIN_STOCK_TEMPLATE,
)
from src.modules.ocr.models import Receta
from src.modules.ocr.providers import (
    Extraido,
    OCRProviderError,
    confianza_supera_umbral,
    get_provider,
    is_test_mode,
)
from src.modules.ocr.schemas import (
    ConfirmarItem,
    Faltante,
    ItemReceta,
    ItemSugerido,
    JobCreadoResponse,
    JobResponse,
    SinStockResponse,
)

logger = logging.getLogger(__name__)

# Documento en memoria solo mientras se procesa; nunca se persiste en disco (LPDP).
_DOCUMENTOS: dict[int, bytes] = {}


class SinStockError(Exception):
    def __init__(self, faltantes: list[Faltante]) -> None:
        self.body = SinStockResponse(
            faltantes=faltantes,
            mensaje=SIN_STOCK_TEMPLATE.format(nombre=faltantes[0].nombre),
        )
        super().__init__(self.body.mensaje)


class JobStateError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class OCRService:
    def __init__(
        self,
        provider=None,
        catalog: Optional[CatalogReadRepository] = None,
        cart_service: Optional[CartService] = None,
        inventory: Optional[LocalMySQLInventoryProvider] = None,
    ) -> None:
        self.provider = provider or get_provider()
        self.catalog = catalog or CatalogReadRepository()
        self.cart_service = cart_service or CartService()
        self.inventory = inventory or LocalMySQLInventoryProvider()

    async def crear_job(
        self,
        session: AsyncSession,
        usuario_id: int,
        nombre_archivo: str,
        contenido: bytes,
    ) -> JobCreadoResponse:
        job = Receta(
            usuario_id=usuario_id,
            estado="procesando",
            nombre_archivo=nombre_archivo,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        _DOCUMENTOS[int(job.id)] = contenido

        if is_test_mode():
            await self.procesar_job(int(job.id), session=session)
        else:
            try:
                await publish_event(QUEUE_NAME, {"job_id": int(job.id)}, timeout=1.0)
            except Exception as exc:
                logger.warning(
                    "No se pudo encolar job OCR %s; se procesa en proceso: %s",
                    job.id,
                    type(exc).__name__,
                )
                await self.procesar_job(int(job.id), session=session)

        settings = get_settings()
        return JobCreadoResponse(
            job_id=int(job.id),
            estado="procesando",
            poll_interval_ms=settings.ocr_poll_interval_ms,
        )

    async def procesar_job(
        self, job_id: int, session: Optional[AsyncSession] = None
    ) -> None:
        propio = session is None
        sm = get_sessionmaker() if propio else None
        db = sm() if propio else session
        try:
            job = await db.get(Receta, job_id)
            if job is None or job.estado != "procesando":
                return
            contenido = _DOCUMENTOS.get(job_id, b"")
            try:
                extraccion = await self.provider.extraer(job.nombre_archivo or "", contenido)
                resueltos = []
                sugeridos = []
                for extraido in extraccion.items:
                    producto, confianza = await self._resolver(extraido)
                    resueltos.append((producto, extraido.cantidad, confianza))
                    sugeridos.append(
                        ItemSugerido(
                            texto=extraido.texto,
                            producto_id=producto.get("id") if producto else None,
                            cantidad=extraido.cantidad,
                            confianza=round(confianza, 2),
                        ).model_dump()
                    )

                if not resueltos or any(
                    producto is None or not confianza_supera_umbral(confianza)
                    for producto, _, confianza in resueltos
                ):
                    job.estado = "requiere_validacion"
                    job.sugeridos_json = json.dumps(sugeridos)
                    job.confianza = round(extraccion.confianza, 2)
                    job.mensaje = LOW_CONFIDENCE_MESSAGE
                else:
                    items = [
                        (producto, cantidad)
                        for producto, cantidad, _ in resueltos
                    ]
                    faltantes = await self._validar_stock(db, items)
                    if faltantes:
                        job.estado = "sin_stock"
                        job.faltantes_json = json.dumps(
                            [faltante.model_dump() for faltante in faltantes]
                        )
                        job.mensaje = SIN_STOCK_TEMPLATE.format(nombre=faltantes[0].nombre)
                    else:
                        await self._completar(db, job, items)
            except OCRProviderError:
                job.estado = "error"
                job.mensaje = ERROR_MESSAGE
            finally:
                job.nombre_archivo = None
                job.actualizado_en = utcnow()
                _DOCUMENTOS.pop(job_id, None)
                await db.commit()
        finally:
            if propio:
                await db.close()

    async def _resolver(self, extraido: Extraido) -> tuple[Optional[dict], float]:
        if extraido.producto_id_hint is not None:
            return (
                {
                    "id": extraido.producto_id_hint,
                    "nombre": extraido.texto,
                    "stock_disponible": 0,
                    "requiere_receta": False,
                    "precio_regular": 0.0,
                    "descuento_porcentaje": 0.0,
                },
                extraido.confianza,
            )
        try:
            producto = await self.catalog.get_by_id(int(extraido.texto))
            return producto, extraido.confianza
        except (ProductNotFoundError, ValueError):
            pass
        items, _, _ = await self.catalog.search("", None, 100)
        mejor: Optional[dict] = None
        mejor_score = 0.0
        objetivo = self._normalizar_texto(extraido.texto)
        for producto in items:
            candidato = self._normalizar_texto(
                f"{producto['nombre']} {producto.get('componentes', '')}"
            )
            score = difflib_ratio(objetivo, candidato)
            if score > mejor_score:
                mejor, mejor_score = producto, score
        return mejor, min(extraido.confianza, mejor_score)

    @staticmethod
    def _normalizar_texto(valor: str) -> str:
        import unicodedata

        normalizado = unicodedata.normalize("NFKD", str(valor).lower())
        return "".join(caracter for caracter in normalizado if not unicodedata.combining(caracter))

    async def _validar_stock(
        self, session: AsyncSession, items: list[tuple[dict, int]]
    ) -> list[Faltante]:
        faltantes: list[Faltante] = []
        for producto, cantidad in items:
            disponible = await self.inventory.get_available_stock(
                session,
                int(producto["id"]),
                int(producto.get("stock_disponible", 0)),
            )
            if cantidad > disponible:
                faltantes.append(
                    Faltante(
                        nombre=str(producto["nombre"]),
                        solicitado=cantidad,
                        disponible=disponible,
                    )
                )
        return faltantes

    async def _completar(
        self, session: AsyncSession, job: Receta, items: list[tuple[dict, int]]
    ) -> None:
        publico = f"REC-{uuid.uuid4().hex[:12]}"
        job.receta_id = publico
        job.estado = "completado"
        job.items_json = json.dumps(
            [
                ItemReceta(
                    producto_id=int(producto["id"]),
                    nombre=str(producto["nombre"]),
                    cantidad=cantidad,
                ).model_dump()
                for producto, cantidad in items
            ]
        )
        job.sugeridos_json = None
        job.faltantes_json = None
        await self._insertar_en_carrito(session, int(job.usuario_id), items, int(job.id))

    async def _insertar_en_carrito(
        self,
        session: AsyncSession,
        usuario_id: int,
        items: list[tuple[dict, int]],
        receta_pk: int,
    ) -> None:
        session_id = f"user:{usuario_id}"
        resultado = await session.execute(
            select(Sesion).where(Sesion.usuario_id == usuario_id).order_by(Sesion.id)
        )
        fila_sesion = resultado.scalars().first()
        if fila_sesion is None:
            fila_sesion = Sesion(
                id=session_id,
                usuario_id=usuario_id,
                ip_address=None,
                creado_en=utcnow(),
                expira_en=utcnow() + timedelta(seconds=get_settings().cart_reservation_ttl_seconds),
            )
            session.add(fila_sesion)
            await session.flush()
        actor = CartActor(
            session_id=fila_sesion.id,
            user_id=usuario_id,
            ip_address=fila_sesion.ip_address or "",
            is_guest=False,
        )
        cart = await self.cart_service._get_or_create_cart(session, actor)
        cart.receta_id = receta_pk
        for producto, cantidad in items:
            producto_id = int(producto["id"])
            item = await self.cart_service._get_item(session, cart.id, producto_id)
            if item is None:
                session.add(
                    CarritoItem(
                        carrito_id=cart.id,
                        producto_id=producto_id,
                        cantidad=cantidad,
                        cantidad_reservada=0,
                        precio_unitario=float(producto.get("precio_regular", 0)),
                        descuento_porcentaje=float(producto.get("descuento_porcentaje", 0)),
                    )
                )
            else:
                item.cantidad += cantidad
        await session.flush()

    async def estado_job(
        self, session: AsyncSession, job_id: int | str, usuario_id: int
    ) -> JobResponse:
        job = await self._job_propio(session, job_id, usuario_id)
        return JobResponse(
            estado=job.estado,
            receta_id=job.receta_id,
            items=json.loads(job.items_json or "[]"),
            items_sugeridos=json.loads(job.sugeridos_json or "[]"),
            faltantes=json.loads(job.faltantes_json or "[]"),
            confianza=job.confianza,
            mensaje=job.mensaje,
        )

    async def confirmar(
        self,
        session: AsyncSession,
        job_id: int | str,
        usuario_id: int,
        items: list[ConfirmarItem],
    ) -> JobResponse:
        job = await self._job_propio(session, job_id, usuario_id)
        if job.estado != "requiere_validacion":
            raise JobStateError("El job no está en validación asistida.")
        resueltos: list[tuple[dict, int]] = []
        for item in items:
            try:
                producto = await self.catalog.get_by_id(item.producto_id)
            except ProductNotFoundError as exc:
                raise HTTPException(status_code=422, detail="Producto no válido.") from exc
            resueltos.append((producto, item.cantidad))
        faltantes = await self._validar_stock(session, resueltos)
        if faltantes:
            raise SinStockError(faltantes)
        await self._completar(session, job, resueltos)
        job.nombre_archivo = None
        job.actualizado_en = utcnow()
        _DOCUMENTOS.pop(int(job.id), None)
        await session.commit()
        return JobResponse(
            estado=job.estado,
            receta_id=job.receta_id,
            items=json.loads(job.items_json or "[]"),
        )

    async def _job_propio(
        self, session: AsyncSession, job_id: int | str, usuario_id: int
    ) -> Receta:
        try:
            identificador = int(job_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=404, detail="Job OCR no encontrado.")
        job = await session.get(Receta, identificador)
        if job is None or int(job.usuario_id) != int(usuario_id):
            raise HTTPException(status_code=404, detail="Job OCR no encontrado.")
        return job


def difflib_ratio(primero: str, segundo: str) -> float:
    from difflib import SequenceMatcher

    return SequenceMatcher(None, primero, segundo).ratio()
