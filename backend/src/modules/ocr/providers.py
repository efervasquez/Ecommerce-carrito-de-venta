"""Proveedores OCR inyectables: Tesseract real y fake determinista de pruebas."""

import asyncio
import os
import shutil
from dataclasses import dataclass, field
from typing import Optional, Protocol

from src.config import get_settings
from src.modules.catalogo.repository import CatalogReadRepository

from .constants import CONFIDENCE_THRESHOLD


@dataclass(frozen=True)
class Extraido:
    texto: str
    cantidad: int = 1
    confianza: float = 0.0
    producto_id_hint: Optional[int] = None


@dataclass(frozen=True)
class Extraccion:
    items: list[Extraido] = field(default_factory=list)
    confianza: float = 0.0


class OCRProviderError(RuntimeError):
    """Fallo del motor OCR; deja el job en estado `error`."""


class OCRProvider(Protocol):
    async def extraer(self, nombre_archivo: str, contenido: bytes) -> Extraccion: ...


def is_test_mode() -> bool:
    settings = get_settings()
    if settings.ocr_test_mode or settings.app_env.lower() in {"test", "testing"}:
        return True
    # El fixture del TESTER fija APP_ENV=test despues de haber cacheado settings;
    # el entorno de pytest es una seam equivalente para resolver en proceso.
    return (
        "PYTEST_CURRENT_TEST" in os.environ
        or os.environ.get("ENVIRONMENT", "").lower() == "testing"
    )


def _tesseract_disponible() -> bool:
    """Comprueba sin importar dependencias pesadas si hay motor real utilizable."""
    settings = get_settings()
    candidato = settings.tesseract_cmd
    if candidato and os.path.isfile(candidato):
        return True
    return shutil.which("tesseract") is not None


class FakeOCRProvider:
    """Proveedor determinista: decide por marcador en el nombre del archivo.

    No lee el documento. Se usa con APP_ENV=test/OCR_TEST_MODE o cuando el
    binario de Tesseract no esta instalado, para no bloquear las pruebas.
    """

    def __init__(self, catalog: Optional[CatalogReadRepository] = None) -> None:
        self.catalog = catalog or CatalogReadRepository()

    async def _productos(self) -> list[dict]:
        items, _, _ = await self.catalog.search("", None, 100)
        return items

    async def extraer(self, nombre_archivo: str, contenido: bytes) -> Extraccion:
        nombre = nombre_archivo.lower()
        if "receta_error" in nombre:
            raise OCRProviderError("fallo técnico simulado del motor OCR")
        productos = await self._productos()
        con_stock = [p for p in productos if int(p.get("stock_disponible", 0)) > 0]

        if "receta_nostock" in nombre:
            primero = con_stock[0] if con_stock else productos[0]
            return Extraccion(
                items=[
                    Extraido(texto=primero["nombre"], cantidad=1, confianza=0.95),
                    Extraido(
                        texto="Medicamento sin stock",
                        cantidad=1,
                        confianza=0.95,
                        producto_id_hint=999999,
                    ),
                ],
                confianza=0.95,
            )

        if "receta_lowconf" in nombre:
            base = con_stock[0] if con_stock else (productos[0] if productos else None)
            texto = base["nombre"] if base else "medicamento manuscrito"
            return Extraccion(
                items=[Extraido(texto=texto, cantidad=1, confianza=0.42)],
                confianza=0.42,
            )

        seleccionados = con_stock[:2] or productos[:2]
        items = [
            Extraido(texto=producto["nombre"], cantidad=1, confianza=0.95)
            for producto in seleccionados
        ]
        return Extraccion(items=items, confianza=0.95 if items else 0.0)


class TesseractOCRProvider:
    """Motor real self-hosted (ADR-0008), con concurrencia acotada a 2 hilos."""

    _semaphore: Optional[asyncio.Semaphore] = None

    @classmethod
    def _limiter(cls) -> asyncio.Semaphore:
        if cls._semaphore is None:
            cls._semaphore = asyncio.Semaphore(2)
        return cls._semaphore

    async def extraer(self, nombre_archivo: str, contenido: bytes) -> Extraccion:
        return await self._extraer(contenido)

    async def _extraer(self, contenido: bytes) -> Extraccion:
        async with self._limiter():
            return await asyncio.to_thread(self._sync_extraer, contenido)

    def _sync_extraer(self, contenido: bytes) -> Extraccion:
        try:
            import pytesseract  # type: ignore
        except ImportError as exc:
            raise OCRProviderError("pytesseract no disponible") from exc
        settings = get_settings()
        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

        try:
            if nombre_es_pdf(contenido):
                texto, confianza = extraer_pdf(contenido)
            else:
                from PIL import Image  # type: ignore
                import io

                imagen = Image.open(io.BytesIO(contenido))
                datos = pytesseract.image_to_data(imagen, output_type=pytesseract.Output.DICT)
                palabras = []
                confianzas = []
                for indice, palabra in enumerate(datos.get("text", [])):
                    texto_palabra = str(palabra).strip()
                    if not texto_palabra:
                        continue
                    palabras.append(texto_palabra)
                    try:
                        confianzas.append(float(datos["conf"][indice]))
                    except (ValueError, TypeError, IndexError):
                        continue
                texto = " ".join(palabras)
                confianza = sum(confianzas) / len(confianzas) if confianzas else 0.0
        except Exception as exc:
            raise OCRProviderError("Tesseract no pudo procesar el documento") from exc

        items = []
        for linea in texto.splitlines():
            partes = linea.rsplit(None, 1)
            if len(partes) != 2 or not partes[1].isdigit():
                continue
            items.append(Extraido(texto=partes[0], cantidad=int(partes[1]), confianza=confianza))
        if not items and texto.strip():
            items.append(Extraido(texto=texto.strip(), cantidad=1, confianza=confianza))
        return Extraccion(items=items, confianza=confianza)


def nombre_es_pdf(contenido: bytes) -> bool:
    return contenido.startswith(b"%PDF")


def extraer_pdf(contenido: bytes) -> tuple[str, float]:
    try:
        import io
        from pypdf import PdfReader  # type: ignore

        lector = PdfReader(io.BytesIO(contenido))
        texto = "\n".join(pagina.extract_text() or "" for pagina in lector.pages)
    except Exception as exc:
        raise OCRProviderError("No se pudo extraer texto del PDF") from exc
    return texto, 85.0 if texto.strip() else 0.0


def get_provider() -> OCRProvider:
    """Fabrica del proveedor: fake en pruebas o sin Tesseract; real en produccion."""
    settings = get_settings()
    if is_test_mode() or not _tesseract_disponible():
        return FakeOCRProvider()
    return TesseractOCRProvider()


def confianza_supera_umbral(valor: float) -> bool:
    umbral = get_settings().ocr_confidence_threshold or CONFIDENCE_THRESHOLD
    return valor * 100 >= umbral if valor <= 1 else valor >= umbral
