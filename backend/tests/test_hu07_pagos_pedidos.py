"""Pruebas de caja negra para HU-07 (checkout, entrega, webhook, pagos y pedidos).

Escritas desde `contratos/CONTRATO-HU-07.md` v1 (aprobado), sin inspeccionar la
implementacion. Las rutas, campos, codigos y textos se toman de la seccion
"Nombres que no se negocian" y de la tabla de comportamiento del contrato.
"""

import asyncio
import hashlib
import hmac
import json
import os
import re
import time
import uuid

import pytest
import pytest_asyncio
import pymysql

CHECKOUT = "/api/v1/checkout"
ZONAS = "/api/v1/zonas"
DIRECCIONES = "/api/v1/direcciones"
WEBHOOK = "/api/v1/pagos/webhook"
PAGOS = "/api/v1/pagos"
PEDIDOS = "/api/v1/pedidos"
CART = "/api/v1/carrito"
CART_ITEMS = "/api/v1/carrito/items"
CATALOG = "/api/v1/catalogo/buscar"
REGISTRO = "/api/v1/auth/registro"
ACTIVAR = "/api/v1/auth/activar"
LOGIN = "/api/v1/auth/login"
QUEUE = "email.auth"

PASSWORD = "Password123!"
EMPTY_CART_MESSAGE = "El carrito está vacío"
ZONA_MESSAGE = "Zona no disponible"
STOCK_MESSAGE = "Stock máximo disponible alcanzado"
ORDER_NUMBER_RE = re.compile(r"^BL-\d+$")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_test")


@pytest_asyncio.fixture
async def api_client(app):
    import httpx
    from httpx import ASGITransport

    host = f"hu07-{uuid.uuid4().hex}"
    transport = ASGITransport(app=app, client=(host, 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture(autouse=True)
def reset_shared_inventory(default_env):
    """Inventario limpio por prueba (mismo criterio que HU-05)."""
    connection = pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "test_user"),
        password=os.environ.get("MYSQL_PASSWORD", "test_password"),
        database=os.environ.get("MYSQL_DB", "test_botica"),
        autocommit=True,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM inventario_stock")
    finally:
        connection.close()
    yield


async def _rabbit_queue():
    import aio_pika

    connection = await aio_pika.connect_robust(
        os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    )
    channel = await connection.channel()
    queue = await channel.declare_queue(QUEUE, durable=True)
    return connection, queue


async def consume_auth_event(timeout: float = 10.0) -> dict:
    connection, queue = await _rabbit_queue()
    try:
        async with queue.iterator(timeout=1) as iterator:
            message = await asyncio.wait_for(iterator.__anext__(), timeout=timeout)
            async with message.process():
                return json.loads(message.body)
    finally:
        await connection.close()


async def create_authenticated_headers(client) -> dict[str, str]:
    email = f"hu07.{uuid.uuid4().hex[:12]}@ejemplo.com"
    connection, queue = await _rabbit_queue()
    try:
        await queue.purge()
    finally:
        await connection.close()
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


async def get_any_product(client) -> dict:
    products = await get_catalog_products(client)
    assert products, "El seed debe exponer productos"
    return products[0]


async def add_item(client, product_id: int, quantity: int = 1, headers: dict | None = None):
    return await client.post(
        CART_ITEMS,
        json={"producto_id": product_id, "cantidad": quantity},
        headers=headers,
    )


async def cart_with_item(client, *, headers=None, quantity=1) -> dict:
    product = await get_any_product(client)
    added = await add_item(client, product["id"], quantity, headers)
    assert added.status_code == 200, added.text
    return product


def stock_row(product_id: int):
    connection = pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "test_user"),
        password=os.environ.get("MYSQL_PASSWORD", "test_password"),
        database=os.environ.get("MYSQL_DB", "test_botica"),
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT disponible, reservado FROM inventario_stock WHERE producto_id = %s",
                (product_id,),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def stripe_signature(payload: bytes, secret: str = WEBHOOK_SECRET) -> dict[str, str]:
    timestamp = int(time.time())
    signed = str(timestamp).encode() + b"." + payload
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return {"Stripe-Signature": f"t={timestamp},v1={digest}"}


def intent_event(event_type: str, payment_intent_id: str) -> dict:
    return {
        "id": f"evt_{uuid.uuid4().hex}",
        "object": "event",
        "type": event_type,
        "data": {
            "object": {
                "id": payment_intent_id,
                "object": "payment_intent",
                "amount": 2400,
                "currency": "pen",
                "metadata": {},
                "status": (
                    "succeeded"
                    if event_type == "payment_intent.succeeded"
                    else "requires_payment_method"
                ),
            }
        },
    }


async def post_webhook(client, event: dict, *, valid: bool = True, include_header: bool = True):
    payload = json.dumps(event).encode()
    headers = {"Content-Type": "application/json"}
    if include_header:
        headers.update(
            stripe_signature(payload) if valid else {"Stripe-Signature": "t=1,v1=invalido"}
        )
    return await client.post(WEBHOOK, content=payload, headers=headers)


def assert_domain_404(response) -> None:
    """Distingue un 404 de dominio de un 404 del router (endpoint aún no implementado)."""
    assert response.status_code == 404, response.text
    body = response.json()
    assert body.get("detail") != "Not Found", f"Endpoint no implementado: {response.text}"


async def auth_checkout(client) -> tuple[dict[str, str], dict]:
    """Carrito autenticado con un item y checkout iniciado (retiro, sin direccion)."""
    headers = await create_authenticated_headers(client)
    product = await cart_with_item(client, headers=headers)
    response = await client.post(CHECKOUT, json={"metodo_entrega": "retiro"}, headers=headers)
    assert response.status_code == 200, response.text
    return headers, response.json()


def assert_no_card_data(body: dict) -> None:
    serialized = json.dumps(body).lower()
    for forbidden in ("card_number", "numero_tarjeta", "cvc", "card[number]"):
        assert forbidden not in serialized


class TestCheckout:
    async def test_guest_reserva_sin_payment_intent(self, api_client):
        await cart_with_item(api_client)
        response = await api_client.post(CHECKOUT, json={})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["requiere_autenticacion"] is True
        assert body["reserva_expira_en"] is not None
        assert "payment_intent_id" not in body
        assert "client_secret" not in body

    async def test_autenticado_devuelve_payment_intent(self, api_client):
        headers = await create_authenticated_headers(api_client)
        await cart_with_item(api_client, headers=headers)
        response = await api_client.post(
            CHECKOUT, json={"metodo_entrega": "retiro"}, headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["payment_intent_id"]
        assert body["client_secret"]
        assert body["monto"] > 0
        assert body["moneda"] == "PEN"
        assert body["reserva_expira_en"] is not None
        assert_no_card_data(body)

    async def test_carrito_vacio_retorna_409(self, api_client):
        headers = await create_authenticated_headers(api_client)
        response = await api_client.post(
            CHECKOUT, json={"metodo_entrega": "retiro"}, headers=headers
        )
        assert response.status_code == 409, response.text
        assert EMPTY_CART_MESSAGE in response.json()["detail"]

    @pytest.mark.parametrize(
        "url",
        [ZONAS, DIRECCIONES, "/api/v1/pagos/pi_desconocido", "/api/v1/pedidos/BL-1"],
    )
    async def test_endpoint_de_pago_sin_sesion_retorna_401(self, api_client, url):
        response = await api_client.get(url)
        assert response.status_code == 401, response.text

    async def test_rate_limit_checkout_por_ip_retorna_429(self, api_client):
        await cart_with_item(api_client)
        responses = await asyncio.gather(
            *(api_client.post(CHECKOUT, json={}) for _ in range(5))
        )
        assert any(response.status_code == 429 for response in responses)

    async def test_guest_con_checkout_activo_retorna_409(self, api_client):
        await cart_with_item(api_client)
        first = await api_client.post(CHECKOUT, json={})
        assert first.status_code == 200, first.text
        second = await api_client.post(CHECKOUT, json={})
        assert second.status_code == 409, second.text

    async def test_direccion_ajena_es_rechazada(self, api_client):
        owner_headers = await create_authenticated_headers(api_client)
        zones = await api_client.get(ZONAS, headers=owner_headers)
        assert zones.status_code == 200, zones.text
        zones_body = zones.json()
        assert zones_body, "El contrato exige seed de al menos una zona activa"
        zone_id = zones_body[0]["id"]

        address = await api_client.post(
            DIRECCIONES,
            json={
                "direccion_linea1": "Av. Prueba 123",
                "telefono_contacto": "999888777",
                "zona_id": zone_id,
            },
            headers=owner_headers,
        )
        assert address.status_code == 201, address.text

        other_headers = await create_authenticated_headers(api_client)
        await cart_with_item(api_client, headers=other_headers)
        response = await api_client.post(
            CHECKOUT,
            json={"metodo_entrega": "delivery", "direccion_id": address.json()["id"]},
            headers=other_headers,
        )
        assert response.status_code in (404, 409), response.text
        if response.status_code == 404:
            assert_domain_404(response)


class TestEntrega:
    async def test_zonas_activas(self, api_client):
        headers = await create_authenticated_headers(api_client)
        response = await api_client.get(ZONAS, headers=headers)
        assert response.status_code == 200, response.text
        zones = response.json()
        assert zones
        for zone in zones:
            assert {"id", "nombre", "distrito", "tiempo_estimado_min"} <= set(zone)

    async def test_crear_y_listar_direcciones(self, api_client):
        headers = await create_authenticated_headers(api_client)
        zones = await api_client.get(ZONAS, headers=headers)
        assert zones.status_code == 200, zones.text
        zone_id = zones.json()[0]["id"]
        created = await api_client.post(
            DIRECCIONES,
            json={
                "direccion_linea1": "Calle Real 456",
                "referencia": "Frente al parque",
                "telefono_contacto": "987654321",
                "zona_id": zone_id,
            },
            headers=headers,
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["id"]
        assert body["direccion_linea1"] == "Calle Real 456"
        assert body["zona_id"] == zone_id

        listed = await api_client.get(DIRECCIONES, headers=headers)
        assert listed.status_code == 200, listed.text
        assert any(item["direccion_linea1"] == "Calle Real 456" for item in listed.json())

    async def test_direccion_incompleta_retorna_422(self, api_client):
        headers = await create_authenticated_headers(api_client)
        response = await api_client.post(
            DIRECCIONES, json={"direccion_linea1": "Solo linea"}, headers=headers
        )
        assert response.status_code == 422, response.text

    async def test_zona_inexistente_retorna_409(self, api_client):
        headers = await create_authenticated_headers(api_client)
        response = await api_client.post(
            DIRECCIONES,
            json={
                "direccion_linea1": "Av. Invalida 1",
                "telefono_contacto": "999000111",
                "zona_id": 999999,
            },
            headers=headers,
        )
        assert response.status_code == 409, response.text
        assert ZONA_MESSAGE in response.json()["detail"]


class TestWebhookExito:
    async def test_succeeded_crea_pedido_vacia_carrito_y_descuenta_stock(self, api_client):
        headers, checkout = await auth_checkout(api_client)
        product = await get_any_product(api_client)
        pi = checkout["payment_intent_id"]

        before = stock_row(product["id"])
        initial_available = before[0] if before else product["stock_disponible"]

        response = await post_webhook(api_client, intent_event("payment_intent.succeeded", pi))
        assert response.status_code == 200, response.text

        status = await api_client.get(f"{PAGOS}/{pi}", headers=headers)
        assert status.status_code == 200, status.text
        status_body = status.json()
        assert status_body["estado"] == "confirmado"
        order = status_body["pedido"]
        assert order is not None
        assert ORDER_NUMBER_RE.match(order["numero"])
        assert order["estado"] == "Registrado"
        assert order["moneda"] == "PEN"

        order_response = await api_client.get(f"{PEDIDOS}/{order['numero']}", headers=headers)
        assert order_response.status_code == 200, order_response.text
        order_body = order_response.json()
        assert order_body["items"]
        assert order_body["monto"] > 0
        assert order_body["moneda"] == "PEN"
        assert "metodo_entrega" in order_body
        assert "entrega" in order_body

        cart = await api_client.get(CART, headers=headers)
        assert cart.status_code == 200, cart.text
        cart_body = cart.json()
        assert cart_body["items_oferta"] == []
        assert cart_body["items_regulares"] == []

        after = stock_row(product["id"])
        assert after is not None, "El webhook debe dejar fila definitiva de inventario"
        assert after[0] <= initial_available - 1, "El stock debe descontarse definitivamente"
        assert after[1] == 0, "La reserva debe convertirse en decremento definitivo"

    async def test_succeeded_duplicado_no_crea_segundo_pedido(self, api_client):
        headers, checkout = await auth_checkout(api_client)
        pi = checkout["payment_intent_id"]
        event = intent_event("payment_intent.succeeded", pi)
        first = await post_webhook(api_client, event)
        assert first.status_code == 200, first.text
        first_order = (await api_client.get(f"{PAGOS}/{pi}", headers=headers)).json()["pedido"]

        second = await post_webhook(api_client, event)
        assert second.status_code == 200, second.text
        second_status = await api_client.get(f"{PAGOS}/{pi}", headers=headers)
        assert second_status.status_code == 200, second_status.text
        assert second_status.json()["pedido"]["numero"] == first_order["numero"]

    async def test_firma_invalida_retorna_400(self, api_client):
        _, checkout = await auth_checkout(api_client)
        event = intent_event("payment_intent.succeeded", checkout["payment_intent_id"])
        response = await post_webhook(api_client, event, valid=False)
        assert response.status_code == 400, response.text

    async def test_firma_ausente_retorna_400(self, api_client):
        _, checkout = await auth_checkout(api_client)
        event = intent_event("payment_intent.succeeded", checkout["payment_intent_id"])
        response = await post_webhook(api_client, event, include_header=False)
        assert response.status_code == 400, response.text


class TestWebhookRechazo:
    async def test_payment_failed_no_crea_pedido_y_conserva_carrito(self, api_client):
        headers, checkout = await auth_checkout(api_client)
        pi = checkout["payment_intent_id"]
        product = await get_any_product(api_client)
        response = await post_webhook(api_client, intent_event("payment_intent.payment_failed", pi))
        assert response.status_code == 200, response.text

        status = await api_client.get(f"{PAGOS}/{pi}", headers=headers)
        assert status.status_code == 200, status.text
        status_body = status.json()
        assert status_body["estado"] == "rechazado"
        assert status_body["pedido"] is None

        cart = await api_client.get(CART, headers=headers)
        assert cart.status_code == 200, cart.text
        cart_body = cart.json()
        items = cart_body["items_oferta"] + cart_body["items_regulares"]
        assert any(item["producto_id"] == product["id"] for item in items)
        assert cart_body["reserva_expira_en"] is None

        after = stock_row(product["id"])
        if after is not None:
            assert after[1] == 0, "La reserva debe liberarse de inmediato"


class TestEstadoPago:
    async def test_pago_procesando_tras_checkout(self, api_client):
        headers, checkout = await auth_checkout(api_client)
        response = await api_client.get(f"{PAGOS}/{checkout['payment_intent_id']}", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["estado"] == "procesando"
        assert body["pedido"] is None

    async def test_pago_rechazado_tras_webhook(self, api_client):
        headers, checkout = await auth_checkout(api_client)
        pi = checkout["payment_intent_id"]
        await post_webhook(api_client, intent_event("payment_intent.payment_failed", pi))
        response = await api_client.get(f"{PAGOS}/{pi}", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["estado"] == "rechazado"

    async def test_pago_ajeno_retorna_404(self, api_client):
        owner_headers, checkout = await auth_checkout(api_client)
        pi = checkout["payment_intent_id"]
        await post_webhook(api_client, intent_event("payment_intent.succeeded", pi))
        other_headers = await create_authenticated_headers(api_client)
        response = await api_client.get(f"{PAGOS}/{pi}", headers=other_headers)
        assert_domain_404(response)


class TestPedido:
    async def test_pedido_propio_y_ajeno(self, api_client):
        owner_headers, checkout = await auth_checkout(api_client)
        pi = checkout["payment_intent_id"]
        await post_webhook(api_client, intent_event("payment_intent.succeeded", pi))
        status = await api_client.get(f"{PAGOS}/{pi}", headers=owner_headers)
        numero = status.json()["pedido"]["numero"]

        own = await api_client.get(f"{PEDIDOS}/{numero}", headers=owner_headers)
        assert own.status_code == 200, own.text

        other_headers = await create_authenticated_headers(api_client)
        foreign = await api_client.get(f"{PEDIDOS}/{numero}", headers=other_headers)
        assert_domain_404(foreign)

    async def test_pedido_inexistente_retorna_404(self, api_client):
        headers = await create_authenticated_headers(api_client)
        response = await api_client.get(f"{PEDIDOS}/BL-999999", headers=headers)
        assert_domain_404(response)


class TestNoVerificado:
    @pytest.mark.skip(
        reason="NO VERIFICADO (contrato, decision 11): provocar inconsistencia fisica para incidencia_stock no es observable en caja negra."
    )
    async def test_incidencia_stock(self, api_client):
        ...

    @pytest.mark.skip(
        reason="NO VERIFICADO: agotar disponibilidad antes del checkout requiere manipular el inventario interno; HU-05 ya cubre el 409 de stock al agregar."
    )
    async def test_checkout_stock_insuficiente_no_contacta_stripe(self, api_client):
        ...
