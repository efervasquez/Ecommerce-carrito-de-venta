import base64
import json
import logging
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Tuple

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)

PRODUCT_FIELDS = [
    "id",
    "nombre",
    "componentes",
    "imagen_url",
    "precio_regular",
    "moneda",
    "descuento_porcentaje",
    "stock_disponible",
    "stock_bajo",
    "precios_bajos",
    "requiere_receta",
]


class CatalogUnavailableError(RuntimeError):
    """El modelo de lectura externo no esta disponible y no hay fallback."""


class CatalogReadRepository:
    """Repositorio de lectura CQRS; Meilisearch es la fuente principal."""

    async def search(
        self, query: str, cursor: str | None, limit: int
    ) -> Tuple[List[Dict[str, Any]], str | None, bool]:
        offset = self._decode_cursor(cursor)
        try:
            return await self._search_meilisearch(query, offset, limit)
        except (httpx.HTTPError, OSError, ValueError) as exc:
            settings = get_settings()
            if not settings.catalog_seed_fallback:
                raise CatalogUnavailableError from exc
            logger.warning("Meilisearch no disponible; usando seed local de catalogo: %s", exc)
            return self._search_seed(query, offset, limit)

    async def _search_meilisearch(
        self, query: str, offset: int, limit: int
    ) -> Tuple[List[Dict[str, Any]], str | None, bool]:
        settings = get_settings()
        headers = {"Authorization": f"Bearer {settings.meilisearch_api_key}"}
        if not settings.meilisearch_api_key:
            headers = {}
        body = {
            "q": query,
            "offset": offset,
            "limit": limit,
            "attributesToRetrieve": PRODUCT_FIELDS,
            "filter": "stock_disponible > 0",
        }
        url = (
            f"{settings.meilisearch_url.rstrip('/')}/indexes/"
            f"{settings.meilisearch_index}/search"
        )
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            payload = response.json()

        items = [self._normalize_product(item) for item in payload.get("hits", [])]
        total = payload.get("estimatedTotalHits")
        has_next = (
            offset + len(items) < int(total)
            if total is not None
            else len(items) == limit
        )
        next_cursor = self._encode_cursor(offset + limit) if has_next else None
        return items, next_cursor, has_next

    def _search_seed(
        self, query: str, offset: int, limit: int
    ) -> Tuple[List[Dict[str, Any]], str | None, bool]:
        products = self._load_seed()
        normalized_query = self._normalize(query)
        if normalized_query:
            scored = []
            for product in products:
                haystack = self._normalize(
                    f"{product['nombre']} {product['componentes']}"
                )
                score = SequenceMatcher(None, normalized_query, haystack).ratio()
                if normalized_query in haystack:
                    score += 1
                if score >= 0.35:
                    scored.append((score, product))
            products = [item for _, item in sorted(scored, key=lambda value: -value[0])]

        visible = products[offset : offset + limit]
        has_next = offset + len(visible) < len(products)
        next_cursor = self._encode_cursor(offset + limit) if has_next else None
        return [self._normalize_product(item) for item in visible], next_cursor, has_next

    def _load_seed(self) -> List[Dict[str, Any]]:
        seed_path = Path(__file__).resolve().parents[4] / "infra" / "catalogo-seed.json"
        with seed_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _normalize_product(product: Dict[str, Any]) -> Dict[str, Any]:
        stock = int(product.get("stock_disponible", 0))
        product = dict(product)
        product["stock_disponible"] = stock
        product["stock_bajo"] = stock < 6
        product["descuento_porcentaje"] = float(product.get("descuento_porcentaje", 0))
        product["precio_regular"] = float(product.get("precio_regular", 0))
        product["moneda"] = product.get("moneda", "PEN")
        product["componentes"] = product.get("componentes", "")
        product["precios_bajos"] = bool(product.get("precios_bajos", False))
        product["requiere_receta"] = bool(product.get("requiere_receta", False))
        return {field: product.get(field) for field in PRODUCT_FIELDS}

    @staticmethod
    def _normalize(value: str) -> str:
        value = unicodedata.normalize("NFKD", value)
        value = "".join(char for char in value if not unicodedata.combining(char))
        return re.sub(r"\s+", " ", value.lower()).strip()

    @staticmethod
    def _encode_cursor(offset: int) -> str:
        return base64.urlsafe_b64encode(str(offset).encode()).decode().rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str | None) -> int:
        if not cursor:
            return 0
        try:
            padded = cursor + "=" * (-len(cursor) % 4)
            offset = int(base64.urlsafe_b64decode(padded.encode()).decode())
            if offset < 0:
                raise ValueError
            return offset
        except (ValueError, UnicodeDecodeError, base64.binascii.Error) as exc:
            raise ValueError("cursor invalido") from exc
