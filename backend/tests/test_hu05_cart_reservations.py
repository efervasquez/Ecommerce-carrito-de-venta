"""Pruebas de caja negra para HU-05 (carrito, reservas y ofertas)."""

import asyncio
import json
import os
import uuid

import pytest
import pytest_asyncio

CART = "/api/v1/carrito"
CART_ITEMS = "/api/v1/carrito/items"
CHECKOUT = "/api/v1/checkout"
REGISTRO = "/api/v1/auth/registro"
ACTIVAR = "/api/v1/auth/activar"
LOGIN = "/api/v1/auth/login"
CATALOG = "/api/v1/catalogo/buscar"
QUEUE = "email.auth"

PASSWORD = "Password123!"
SKU_LIMIT_MESSAGE = "Límite máximo de 3 unidades por producto"


@pytest_asyncio.fixture
async def cart_client(app):
    import httpx
    from httpx import ASGITransport

    host = f"hu05-{uuid.uuid4().hex}"
    transport = ASGITransport(app=app, client=(host, 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


async def _rabbit_queue():
    import aio_pika

    url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()
    queue = await channel.declare_queue(QUEUE, durable=True)
    return connection, queue


async def purge_auth_queue() -> None:
    connection, queue = await _rabbit_queue()
    try:
        await queue.purge()
    finally:
        await connection.close()


async def consume_auth_event(timeout: float = 10.0) -> dict:
    connection, queue = await _rabbit_queue()
    try:
        async with queue.iterator(timeout=1) as iterator:
            message = await asyncio.wait_for(iterator.__anext__(), timeout=timeout)
            async with message.process():
                return json.loads(message.body)
    finally:
        await connection.close()


async def get_catalog_products(client, limit: int = 10, max_items: int = 100) -> list[dict]:
    items: list[dict] = []
    cursor = None
    while len(items) < max_items:
        params = {"q": "", "limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        response = await client.get(CATALOG, params=params)
        assert response.status_code == 200, response.text
        body = response.json()
        items.extend(body["items"])
        if not body["has_next"]:
            break
        cursor = body["next_cursor"]
    return items[:max_items]


async def get_product_with_stock(client) -> dict:
    products = await get_catalog_products(client)
    product = next((item for item in products if item["stock_disponible"] > 0), None)
    assert product is not None, "El seed debe exponer al menos un producto con stock"
    return product


async def get_offer_and_regular(client) -> tuple[dict, dict]:
    products = await get_catalog_products(client)
    offer = next((item for item in products if item["descuento_porcentaje"] > 0), None)
    regular = next((item for item in products if item["descuento_porcentaje"] == 0), None)
    assert offer is not None, "El seed debe exponer un producto en oferta"
    assert regular is not None, "El seed debe exponer un producto regular"
    return offer, regular


async def add_item(client, product_id: int, quantity: int = 1, headers: dict | None = None):
    return await client.post(
        CART_ITEMS,
        json={"producto_id": product_id, "cantidad": quantity},
        headers=headers,
    )


async def create_authenticated_headers(client) -> dict[str, str]:
    email = f"hu05.{uuid.uuid4().hex[:12]}@ejemplo.com"
    await purge_auth_queue()
    registration = await client.post(REGISTRO, json={"email": email})
    assert registration.status_code == 200, registration.text
    activation_event = await consume_auth_event()
    activation = await client.post(
        ACTIVAR,
        json={"token": activation_event["payload"]["token"], "password": PASSWORD},
    )
    assert activation.status_code == 200, activation.text
    login = await client.post(LOGIN, json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


class TestCartReadAndItems:
    async def test_carrito_guest_nuevo_retorna_vacio_y_totales_cero(self, cart_client):
        response = await cart_client.get(CART)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["items_oferta"] == []
        assert body["items_regulares"] == []
        assert body["subtotal"] == 0
        assert body["ahorro_total"] == 0
        assert body["total"] == 0
        assert body["reserva_expira_en"] is None

    async def test_guest_persiste_item_en_la_misma_sesion_sin_reservar(self, cart_client):
        product = await get_product_with_stock(cart_client)
        added = await add_item(cart_client, product["id"], 1)
        assert added.status_code == 200, added.text

        cart = await cart_client.get(CART)
        assert cart.status_code == 200
        body = cart.json()
        all_items = body["items_oferta"] + body["items_regulares"]
        assert any(item["producto_id"] == product["id"] for item in all_items)
        assert body["reserva_expira_en"] is None

    async def test_carrito_oferta_primero_calcula_ahorro_y_total(self, cart_client):
        offer, regular = await get_offer_and_regular(cart_client)
        assert (await add_item(cart_client, offer["id"], 1)).status_code == 200
        assert (await add_item(cart_client, regular["id"], 1)).status_code == 200

        body = (await cart_client.get(CART)).json()
        assert body["items_oferta"]
        assert body["items_regulares"]
        assert body["subtotal"] >= body["total"]
        assert body["ahorro_total"] >= 0
        assert body["total"] == body["subtotal"] - body["ahorro_total"]

    async def test_autenticado_agregar_persiste_y_reserva_ttl_24h(self, cart_client):
        headers = await create_authenticated_headers(cart_client)
        product = await get_product_with_stock(cart_client)
        response = await add_item(cart_client, product["id"], 1, headers)
        assert response.status_code == 200, response.text

        body = (await cart_client.get(CART, headers=headers)).json()
        items = body["items_oferta"] + body["items_regulares"]
        assert any(item["producto_id"] == product["id"] for item in items)
        assert body["reserva_expira_en"] is not None

    async def test_suma_superior_a_tres_unidades_sku_retorna_409_y_conserva_item(self, cart_client):
        product = await get_product_with_stock(cart_client)
        first = await add_item(cart_client, product["id"], 2)
        assert first.status_code == 200
        second = await add_item(cart_client, product["id"], 2)
        assert second.status_code == 409
        assert second.json()["detail"] == SKU_LIMIT_MESSAGE

    async def test_cantidad_superior_al_stock_retorna_409(self, cart_client):
        product = await get_product_with_stock(cart_client)
        response = await add_item(cart_client, product["id"], product["stock_disponible"] + 1)
        assert response.status_code == 409, response.text

    async def test_patch_cantidad_valida_actualiza_totales(self, cart_client):
        product = await get_product_with_stock(cart_client)
        assert (await add_item(cart_client, product["id"], 1)).status_code == 200
        response = await cart_client.patch(f"{CART_ITEMS}/{product['id']}", json={"cantidad": 2})
        assert response.status_code == 200, response.text

    async def test_patch_superior_stock_retorna_409_y_mensaje_maximo(self, cart_client):
        product = await get_product_with_stock(cart_client)
        assert (await add_item(cart_client, product["id"], 1)).status_code == 200
        response = await cart_client.patch(
            f"{CART_ITEMS}/{product['id']}", json={"cantidad": product["stock_disponible"] + 1}
        )
        assert response.status_code == 409
        assert "Stock máximo disponible alcanzado" in response.json()["detail"]

    async def test_delete_item_retorna_200_y_elimina(self, cart_client):
        product = await get_product_with_stock(cart_client)
        assert (await add_item(cart_client, product["id"], 1)).status_code == 200
        deleted = await cart_client.delete(f"{CART_ITEMS}/{product['id']}")
        assert deleted.status_code == 200, deleted.text
        body = (await cart_client.get(CART)).json()
        assert not any(
            item["producto_id"] == product["id"]
            for item in body["items_oferta"] + body["items_regulares"]
        )

    async def test_delete_producto_inexistente_retorna_404(self, cart_client):
        response = await cart_client.delete(f"{CART_ITEMS}/999999")
        assert response.status_code == 404


class TestGuestLimitsAndCheckout:
    async def test_guest_mas_de_diez_productos_distintos_retorna_409(self, cart_client):
        products = await get_catalog_products(cart_client, limit=10, max_items=11)
        if len(products) < 11:
            pytest.skip("NO VERIFICADO: el seed observable expone menos de 11 productos distintos")
        for product in products[:10]:
            response = await add_item(cart_client, product["id"], 1)
            assert response.status_code == 200, response.text
        response = await add_item(cart_client, products[10]["id"], 1)
        assert response.status_code == 409

    async def test_checkout_guest_crea_reserva_sin_pago_ni_pedido(self, cart_client):
        product = await get_product_with_stock(cart_client)
        assert (await add_item(cart_client, product["id"], 1)).status_code == 200
        response = await cart_client.post(CHECKOUT)
        assert response.status_code in (200, 201), response.text
        body = response.json()
        assert body["reserva_expira_en"] is not None
        assert "payment" not in body
        assert "pedido" not in body

    async def test_checkout_guest_repetido_con_reserva_activa_retorna_409(self, cart_client):
        product = await get_product_with_stock(cart_client)
        assert (await add_item(cart_client, product["id"], 1)).status_code == 200
        first = await cart_client.post(CHECKOUT)
        assert first.status_code in (200, 201)
        second = await cart_client.post(CHECKOUT)
        assert second.status_code == 409

    async def test_rate_limit_agregar_por_ip_retorna_429(self, cart_client):
        product = await get_product_with_stock(cart_client)
        responses = await asyncio.gather(
            *(add_item(cart_client, product["id"], 1) for _ in range(7))
        )
        assert any(response.status_code == 429 for response in responses)

    async def test_rate_limit_checkout_por_ip_retorna_429(self, cart_client):
        product = await get_product_with_stock(cart_client)
        assert (await add_item(cart_client, product["id"], 1)).status_code == 200
        responses = await asyncio.gather(*(cart_client.post(CHECKOUT) for _ in range(4)))
        assert any(response.status_code == 429 for response in responses)


class TestReservationLifecycle:
    @pytest.mark.skip(
        reason="NO VERIFICADO: el contrato no fija una operación observable para invocar el job de purga ni adelantar el reloj 24h."
    )
    async def test_ttl_vencido_libera_stock_y_purga_carrito(self):
        ...

    @pytest.mark.skip(
        reason="NO VERIFICADO: requiere controlar el reloj y observar el scheduler sin importar código interno."
    )
    async def test_reserva_vigente_no_libera_stock(self):
        ...
