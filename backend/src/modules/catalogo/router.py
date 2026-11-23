from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.modules.catalogo.schemas import CatalogoResponse, ProductoDetalle
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


@router.get("/productos/{producto_id}", response_model=ProductoDetalle)
async def detalle_producto(
    producto_id: int,
    service: CatalogService = Depends(get_catalog_service),
) -> ProductoDetalle:
    return await service.get_detail(producto_id)
