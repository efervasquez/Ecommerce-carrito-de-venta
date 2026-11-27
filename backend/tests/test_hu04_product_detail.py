"""Pruebas de caja negra para HU-04 (detalle extendido del producto)."""

import uuid

import pytest_asyncio

PRODUCT_DETAIL = "/api/v1/catalogo/productos"
REQUIRED_DETAIL_FIELDS = {
    "id",
    "nombre",
    "imagen_url",
    "componentes",
    "precio_regular",
    "moneda",
    "descuento_porcentaje",
    "requiere_receta",
    "detalle",
    "presentacion",
    "metodos_entrega",
    "contraindicaciones",
    "precauciones_advertencias",
    "reacciones_adversas",
    "precios_bajos",
    "stock_disponible",
}


@pytest_asyncio.fixture
async def detail_client(app):
    import httpx
    from httpx import ASGITransport

    host = f"hu04-{uuid.uuid4().hex}"
    transport = ASGITransport(app=app, client=(host, 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


class TestProductDetailAPI:
    async def test_producto_existente_retorna_payload_completo(self, detail_client):
        response = await detail_client.get(f"{PRODUCT_DETAIL}/1")
        assert response.status_code == 200, response.text
        payload = response.json()
        assert set(payload) == REQUIRED_DETAIL_FIELDS
        assert payload["id"] == 1
        assert isinstance(payload["nombre"], str)
        assert isinstance(payload["componentes"], str)
        assert isinstance(payload["imagen_url"], str)
        assert isinstance(payload["precio_regular"], (int, float))
        assert isinstance(payload["moneda"], str)
        assert isinstance(payload["descuento_porcentaje"], (int, float))
        assert isinstance(payload["requiere_receta"], bool)
        assert isinstance(payload["detalle"], str)
        assert isinstance(payload["presentacion"], str)
        assert isinstance(payload["metodos_entrega"], list)
        assert isinstance(payload["contraindicaciones"], str)
        assert isinstance(payload["precauciones_advertencias"], str)
        assert isinstance(payload["reacciones_adversas"], str)
        assert isinstance(payload["precios_bajos"], bool)
        assert isinstance(payload["stock_disponible"], int)

    async def test_producto_inexistente_retorna_404(self, detail_client):
        response = await detail_client.get(f"{PRODUCT_DETAIL}/999999")
        assert response.status_code == 404, response.text

    async def test_id_no_numerico_retorna_422(self, detail_client):
        response = await detail_client.get(f"{PRODUCT_DETAIL}/no-es-un-id")
        assert response.status_code == 422, response.text
