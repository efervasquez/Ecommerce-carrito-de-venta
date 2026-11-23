"""Pruebas de caja negra para HU-03 (catalogo y busqueda difusa).

Fuente unica: contratos/CONTRATO-HU-03.md v1, aprobada 2026-11-23.
"""

import uuid

import pytest_asyncio

CATALOG_SEARCH = "/api/v1/catalogo/buscar"
REQUIRED_PRODUCT_FIELDS = {
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
}


@pytest_asyncio.fixture
async def catalog_client(app):
    import httpx
    from httpx import ASGITransport

    host = f"catalog-{uuid.uuid4().hex}"
    transport = ASGITransport(app=app, client=(host, 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


def assert_catalog_payload(payload: dict) -> None:
    assert set(payload) == {"items", "next_cursor", "has_next"}
    assert isinstance(payload["items"], list)
    assert payload["next_cursor"] is None or isinstance(payload["next_cursor"], str)
    assert isinstance(payload["has_next"], bool)
    for item in payload["items"]:
        assert set(item) == REQUIRED_PRODUCT_FIELDS


class TestCatalogoAPI:
    async def test_typo_en_nombre_devuelve_ibuprofeno_y_payload_completo(self, catalog_client):
        response = await catalog_client.get(
            CATALOG_SEARCH, params={"q": "ibuprofno 400", "limit": 10}
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert_catalog_payload(payload)
        assert any(
            item["nombre"] == "Ibuprofeno 400mg"
            and "Ibuprofeno" in item["componentes"]
            for item in payload["items"]
        )

    async def test_busqueda_por_componente_devuelve_coincidencias(self, catalog_client):
        response = await catalog_client.get(
            CATALOG_SEARCH, params={"q": "Ibuprofeno", "limit": 10}
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert_catalog_payload(payload)
        assert payload["items"]
        assert all(
            "ibuprofeno" in (item["nombre"] + " " + item["componentes"]).lower()
            for item in payload["items"]
        )

    async def test_q_vacio_devuelve_primera_tanda_y_cursor(self, catalog_client):
        response = await catalog_client.get(CATALOG_SEARCH, params={"q": "", "limit": 2})
        assert response.status_code == 200, response.text
        payload = response.json()
        assert_catalog_payload(payload)
        assert len(payload["items"]) <= 2
        if payload["has_next"]:
            assert payload["next_cursor"]

    async def test_cursor_limit_carga_siguiente_tanda_sin_duplicados(self, catalog_client):
        first = await catalog_client.get(CATALOG_SEARCH, params={"q": "", "limit": 2})
        assert first.status_code == 200, first.text
        first_payload = first.json()
        assert_catalog_payload(first_payload)
        if not first_payload["has_next"]:
            return

        second = await catalog_client.get(
            CATALOG_SEARCH,
            params={"q": "", "cursor": first_payload["next_cursor"], "limit": 2},
        )
        assert second.status_code == 200, second.text
        second_payload = second.json()
        assert_catalog_payload(second_payload)
        first_ids = {item["id"] for item in first_payload["items"]}
        second_ids = {item["id"] for item in second_payload["items"]}
        assert first_ids.isdisjoint(second_ids)

    async def test_sin_resultados_devuelve_items_vacio(self, catalog_client):
        response = await catalog_client.get(
            CATALOG_SEARCH, params={"q": "producto-sin-coincidencias-9f7e", "limit": 10}
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert_catalog_payload(payload)
        assert payload["items"] == []

    async def test_limit_cero_retorna_422(self, catalog_client):
        response = await catalog_client.get(CATALOG_SEARCH, params={"q": "ibuprofeno", "limit": 0})
        assert response.status_code == 422, response.text

    async def test_limit_ausente_retorna_422(self, catalog_client):
        response = await catalog_client.get(CATALOG_SEARCH, params={"q": "ibuprofeno"})
        assert response.status_code == 422, response.text

    async def test_rate_limit_mas_de_20_consultas_por_ip_retorna_429(self, catalog_client):
        responses = [
            await catalog_client.get(
                CATALOG_SEARCH,
                params={"q": "consulta-sin-resultados", "limit": 1},
            )
            for _ in range(21)
        ]
        too_many = [response for response in responses if response.status_code == 429]
        assert too_many, [response.status_code for response in responses]
