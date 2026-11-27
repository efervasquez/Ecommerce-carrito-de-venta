from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.modules.catalogo.schemas import CatalogoResponse
from src.modules.catalogo.service import CatalogService

router = APIRouter(prefix="/catalogo", tags=["Catalogo"])


def get_catalog_service() -> CatalogService:
    return CatalogService()


@router.get("/buscar", response_model=CatalogoResponse)
async def buscar_catalogo(
    q: str = Query(default=""),
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(..., ge=1, le=50),
    service: CatalogService = Depends(get_catalog_service),
) -> CatalogoResponse:
    return await service.search(q, cursor, limit)
