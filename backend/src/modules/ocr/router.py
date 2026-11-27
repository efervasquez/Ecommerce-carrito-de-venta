"""Endpoints OCR de recetas: subida, polling y validación asistida."""

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.modules.ocr.constants import (
    FORMATO_MESSAGE,
    MAX_FILE_BYTES,
    ALLOWED_EXTENSIONS,
    TAMANO_MESSAGE,
)
from src.modules.ocr.schemas import (
    ConfirmarInput,
    JobCreadoResponse,
    JobResponse,
)
from src.modules.ocr.service import JobStateError, OCRService, SinStockError
from src.modules.pagos.auth import require_user_id

router = APIRouter(tags=["OCR"])


def get_ocr_service() -> OCRService:
    return OCRService()


def _extraer_archivo(body: bytes, boundary: str) -> Optional[tuple[str, bytes]]:
    delimitador = b"--" + boundary.encode()
    for parte in body.split(delimitador):
        parte = parte.strip(b"\r\n")
        if not parte or parte == b"--":
            continue
        cabeceras, separador, datos = parte.partition(b"\r\n\r\n")
        if not separador:
            continue
        cabecera_texto = cabeceras.decode("utf-8", "ignore")
        if 'name="archivo"' not in cabecera_texto:
            continue
        encontrado = re.search(r'filename="([^"]*)"', cabecera_texto)
        nombre = encontrado.group(1) if encontrado else "archivo"
        return nombre, datos.rstrip(b"\r\n")
    return None


@router.post("/ocr/recetas", response_model=JobCreadoResponse, status_code=202)
async def subir_receta(
    request: Request,
    usuario_id: int = Depends(require_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: OCRService = Depends(get_ocr_service),
) -> JobCreadoResponse:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type or "boundary=" not in content_type:
        raise HTTPException(status_code=422, detail=FORMATO_MESSAGE)
    boundary = content_type.split("boundary=", 1)[1].split(";", 1)[0].strip().strip('"')
    archivo = _extraer_archivo(await request.body(), boundary)
    if archivo is None:
        raise HTTPException(status_code=422, detail="El campo archivo es requerido.")
    nombre, contenido = archivo
    extension = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail=FORMATO_MESSAGE)
    if len(contenido) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail=TAMANO_MESSAGE)
    return await service.crear_job(session, usuario_id, nombre, contenido)


@router.get("/ocr/jobs/{job_id}", response_model=JobResponse)
async def consultar_job(
    job_id: str,
    usuario_id: int = Depends(require_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: OCRService = Depends(get_ocr_service),
) -> JobResponse:
    return await service.estado_job(session, job_id, usuario_id)


@router.post("/ocr/jobs/{job_id}/confirmar", response_model=JobResponse)
async def confirmar_job(
    job_id: str,
    payload: ConfirmarInput,
    usuario_id: int = Depends(require_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: OCRService = Depends(get_ocr_service),
):
    try:
        return await service.confirmar(session, job_id, usuario_id, payload.items)
    except SinStockError as exc:
        return JSONResponse(status_code=409, content=exc.body.model_dump())
    except JobStateError as exc:
        raise HTTPException(status_code=409, detail=exc.detail) from exc
