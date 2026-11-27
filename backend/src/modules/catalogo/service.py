from typing import Optional

from fastapi import HTTPException

from src.modules.catalogo.repository import CatalogReadRepository, CatalogUnavailableError
from src.modules.catalogo.schemas import CatalogoResponse, ProductoCatalogo


class CatalogService:
    """Servicio de lectura del catalogo (CQRS, sin operaciones de escritura)."""

    def __init__(self, repository: Optional[CatalogReadRepository] = None) -> None:
        self.repository = repository or CatalogReadRepository()

    async def search(self, query: str, cursor: str | None, limit: int) -> CatalogoResponse:
        try:
            items, next_cursor, has_next = await self.repository.search(query, cursor, limit)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Cursor inválido") from exc
        except CatalogUnavailableError as exc:
            raise HTTPException(
                status_code=503, detail="El catálogo no está disponible."
            ) from exc
        return CatalogoResponse(
            items=[ProductoCatalogo(**item) for item in items],
            next_cursor=next_cursor,
            has_next=has_next,
        )
