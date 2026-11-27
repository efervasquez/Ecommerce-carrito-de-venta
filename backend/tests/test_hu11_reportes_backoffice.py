"""Pruebas de caja negra para HU-11 (reporteria y metricas del backoffice).

Escritas desde `contratos/CONTRATO-HU-11.md` v1 (aprobado), sin inspeccionar la
implementacion. Rutas, campos, roles y textos se toman de la seccion "Nombres que
no se negocian" y de las tablas de comportamiento del contrato.

Los reportes son de solo lectura. Las aserciones de conteos exactos se limitan a
un rango futuro sin pedidos (2099) para no depender de la BD compartida; el resto
valida estructura, tipos, invariantes y sumas.
"""

import asyncio
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from datetime import date

import pytest

# ---------------------------------------------------------------------------
# Semilla de usuarios RBAC (admin / motorizado). Se fija antes de que
# `src.main` cargue la configuracion para que el seed del DEV cree los usuarios.
# `setdefault` respeta los valores ya fijados por otros modulos de la sesion.
# ---------------------------------------------------------------------------
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SEED_RBAC_USERS", "true")

ADMIN_EMAIL = os.environ.setdefault("SEED_ADMIN_EMAIL", "hu11.admin@ejemplo.com")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "Admin12345!")
MOTORIZADO_EMAIL = os.environ.setdefault("SEED_MOTORIZADO_EMAIL", "hu11.motorizado@ejemplo.com")
os.environ.setdefault("SEED_MOTORIZADO_PASSWORD", "Moto12345!")

ADMIN_PASSWORD = os.environ["SEED_ADMIN_PASSWORD"]
MOTORIZADO_PASSWORD = os.environ["SEED_MOTORIZADO_PASSWORD"]

REPORTES = "/api/v1/backoffice/reportes"
VENTAS = f"{REPORTES}/ventas"
BALANCE = f"{REPORTES}/pedidos-balance"
CRITICO = f"{REPORTES}/inventario-critico"

CHECKOUT = "/api/v1/checkout"
PAGOS = "/api/v1/pagos"
WEBHOOK = "/api/v1/pagos/webhook"
CART_ITEMS = "/api/v1/carrito/items"
CATALOG = "/api/v1/catalogo/buscar"
REGISTRO = "/api/v1/auth/registro"
ACTIVAR = "/api/v1/auth/activar"
LOGIN = "/api/v1/auth/login"
QUEUE = "email.auth"

PASSWORD = "Password123!"
MSG_RBAC = "Acceso restringido a administradores y supervisores."
MSG_RANGO = "La fecha de fin no puede ser anterior a la fecha de inicio."
MSG_FORMATO = "El formato de fecha debe ser YYYY-MM-DD."
ESTADOS = ("Registrado", "Preparando producto", "En camino", "Entregado")
FECHA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_test")


# ---------------------------------------------------------------------------
# Clientes con IP propia (evita el rate limit de auth compartido por IP).
# ---------------------------------------------------------------------------
@pytest.fixture
def make_client(app):
    def _make():
        import httpx
        from httpx import ASGITransport

        host = f"hu11-{uuid.uuid4().hex}"
        transport = ASGITransport(app=app, client=(host, 50000))
        return httpx.AsyncClient(transport=transport, base_url="http://testserver")

    return _make


# ---------------------------------------------------------------------------
# Helpers de autenticacion.
# ---------------------------------------------------------------------------
async def _rabbit_queue():
    import aio_pika

    url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()
    queue = await channel.declare_queue(QUEUE, durable=True)
    return connection, channel, queue


async def consume_activation_event(timeout: float = 10.0) -> dict:
    connection, channel, queue = await _rabbit_queue()
    try:
        async with queue.iterator(timeout=1) as iterator:
            message = await asyncio.wait_for(iterator.__anext__(), timeout=timeout)
            async with message.process():
                return json.loads(message.body)
    finally:
        await connection.close()


async def purge_activation_queue() -> None:
    connection, channel, queue = await _rabbit_queue()
    try:
        await queue.purge()
    finally:
        await connection.close()


async def cliente_headers(client) -> dict[str, str]:
    await purge_activation_queue()
    email = f"hu11.{uuid.uuid4().hex[:12]}@ejemplo.com"
    registration = await client.post(REGISTRO, json={"email": email})
    assert registration.status_code == 200, registration.text
    event = await consume_activation_event()
    activation = await client.post(
        ACTIVAR, json={"token": event["payload"]["token"], "password": PASSWORD}
    )
    assert activation.status_code == 200, activation.text
    login = await client.post(LOGIN, json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def login_seeded(client, email: str, password: str) -> dict[str, str]:
    response = await client.post(LOGIN, json={"email": email, "password": password})
    assert response.status_code == 200, (
        f"El seed de usuarios RBAC no creo '{email}' (APP_ENV=test): {response.text}"
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def admin_session(make_client) -> dict:
    client = make_client()
    headers = await login_seeded(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    return {"client": client, "headers": headers}


async def motorizado_session(make_client) -> dict:
    client = make_client()
    headers = await login_seeded(client, MOTORIZADO_EMAIL, MOTORIZADO_PASSWORD)
    return {"client": client, "headers": headers}


# ---------------------------------------------------------------------------
# Helpers de pedido confirmado (flujo real HU-07, entrega en botica).
# ---------------------------------------------------------------------------
async def get_any_product(client) -> dict:
    response = await client.get(CATALOG, params={"q": "", "limit": 10})
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert items, "El seed debe exponer productos"
    return max(items, key=lambda p: p.get("stock_disponible", 0))


def stripe_signature(payload: bytes, secret: str = WEBHOOK_SECRET) -> dict[str, str]:
    timestamp = int(time.time())
    signed = str(timestamp).encode() + b"." + payload
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return {"Stripe-Signature": f"t={timestamp},v1={digest}"}


def intent_event(payment_intent_id: str) -> dict:
    return {
        "id": f"evt_{uuid.uuid4().hex}",
        "object": "event",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": payment_intent_id,
                "object": "payment_intent",
                "amount": 2400,
                "currency": "pen",
                "metadata": {},
                "status": "succeeded",
            }
        },
    }


async def crear_pedido_confirmado(make_client) -> dict:
    """Crea un pedido `Registrado` pagado por el flujo real de HU-07 (retiro)."""
    client = make_client()
    headers = await cliente_headers(client)
    product = await get_any_product(client)

    added = await client.post(
        CART_ITEMS,
        json={"producto_id": product["id"], "cantidad": 1},
        headers=headers,
    )
    assert added.status_code == 200, added.text

    checkout = await client.post(
        CHECKOUT, json={"metodo_entrega": "retiro"}, headers=headers
    )
    assert checkout.status_code == 200, checkout.text
    checkout_body = checkout.json()
    payment_intent_id = checkout_body["payment_intent_id"]

    payload = json.dumps(intent_event(payment_intent_id)).encode()
    hook_headers = {"Content-Type": "application/json"}
    hook_headers.update(stripe_signature(payload))
    hook = await client.post(WEBHOOK, content=payload, headers=hook_headers)
    assert hook.status_code == 200, hook.text

    status = await client.get(f"{PAGOS}/{payment_intent_id}", headers=headers)
    assert status.status_code == 200, status.text
    pedido = status.json()["pedido"]
    assert pedido is not None, "El pago confirmado debe crear un pedido"
    assert pedido["estado"] == "Registrado"
    return {"numero": pedido["numero"], "monto": checkout_body["monto"]}


# ---------------------------------------------------------------------------
# Utilidades de validacion de respuestas.
# ---------------------------------------------------------------------------
def assert_entero_no_negativo(valor, campo: str) -> None:
    assert isinstance(valor, (int, float)) and float(valor).is_integer(), (
        f"'{campo}' debe ser un entero: {valor!r}"
    )
    assert float(valor) >= 0, f"'{campo}' no puede ser negativo: {valor!r}"


def assert_fecha_iso(valor, campo: str) -> None:
    assert isinstance(valor, str) and FECHA_ISO.match(valor), (
        f"'{campo}' debe tener formato YYYY-MM-DD: {valor!r}"
    )
    date.fromisoformat(valor)


# ---------------------------------------------------------------------------
# RBAC (contrato §1).
# ---------------------------------------------------------------------------
class TestRBAC:
    ENDPOINTS = [VENTAS, BALANCE, CRITICO]

    @pytest.mark.parametrize("url", ENDPOINTS)
    async def test_sin_sesion_retorna_401(self, make_client, url):
        client = make_client()
        response = await client.get(url)
        assert response.status_code == 401, response.text

    @pytest.mark.parametrize("url", ENDPOINTS)
    async def test_motorizado_retorna_403(self, make_client, url):
        actor = await motorizado_session(make_client)
        response = await actor["client"].get(url, headers=actor["headers"])
        assert response.status_code == 403, response.text
        assert response.json()["detail"] == MSG_RBAC

    async def test_cliente_retorna_403_en_los_tres_reportes(self, make_client):
        client = make_client()
        headers = await cliente_headers(client)
        for url in self.ENDPOINTS:
            response = await client.get(url, headers=headers)
            assert response.status_code == 403, f"{url}: {response.text}"
            assert response.json()["detail"] == MSG_RBAC

    @pytest.mark.parametrize("url", ENDPOINTS)
    async def test_admin_retorna_200(self, make_client, url):
        admin = await admin_session(make_client)
        response = await admin["client"].get(url, headers=admin["headers"])
        assert response.status_code == 200, f"{url}: {response.text}"


# ---------------------------------------------------------------------------
# Reporte consolidado de ventas (contrato §2).
# ---------------------------------------------------------------------------
class TestVentas:
    async def test_rango_valido_devuelve_la_estructura_del_contrato(self, make_client):
        admin = await admin_session(make_client)
        response = await admin["client"].get(
            VENTAS,
            params={"fecha_inicio": "2026-10-01", "fecha_fin": "2026-10-31"},
            headers=admin["headers"],
        )
        assert response.status_code == 200, response.text
        body = response.json()

        for campo in (
            "fecha_inicio",
            "fecha_fin",
            "total_ordenes",
            "unidades_vendidas",
            "monto_total_facturado",
            "moneda",
        ):
            assert campo in body, f"Falta el campo '{campo}': {body}"

        assert body["fecha_inicio"] == "2026-10-01"
        assert body["fecha_fin"] == "2026-10-31"
        assert body["moneda"] == "PEN"
        assert_entero_no_negativo(body["total_ordenes"], "total_ordenes")
        assert_entero_no_negativo(body["unidades_vendidas"], "unidades_vendidas")
        assert float(body["monto_total_facturado"]) >= 0

    async def test_rango_futuro_sin_pedidos_devuelve_ceros(self, make_client):
        admin = await admin_session(make_client)
        response = await admin["client"].get(
            VENTAS,
            params={"fecha_inicio": "2099-01-01", "fecha_fin": "2099-01-31"},
            headers=admin["headers"],
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["fecha_inicio"] == "2099-01-01"
        assert body["fecha_fin"] == "2099-01-31"
        assert int(body["total_ordenes"]) == 0
        assert int(body["unidades_vendidas"]) == 0
        assert float(body["monto_total_facturado"]) == 0.0

    async def test_fecha_fin_anterior_retorna_422(self, make_client):
        admin = await admin_session(make_client)
        response = await admin["client"].get(
            VENTAS,
            params={"fecha_inicio": "2026-10-31", "fecha_fin": "2026-10-01"},
            headers=admin["headers"],
        )
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_RANGO

    @pytest.mark.parametrize(
        "params",
        [
            {"fecha_inicio": "31-10-2026", "fecha_fin": "2026-10-31"},
            {"fecha_inicio": "2026-10-01", "fecha_fin": "31-10-2026"},
            {"fecha_inicio": "2026/10/01", "fecha_fin": "2026-10-31"},
        ],
    )
    async def test_formato_de_fecha_invalido_retorna_422(self, make_client, params):
        admin = await admin_session(make_client)
        response = await admin["client"].get(
            VENTAS, params=params, headers=admin["headers"]
        )
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_FORMATO

    async def test_sin_parametros_toma_un_rango_por_defecto(self, make_client):
        admin = await admin_session(make_client)
        response = await admin["client"].get(VENTAS, headers=admin["headers"])
        assert response.status_code == 200, response.text
        body = response.json()
        assert_fecha_iso(body.get("fecha_inicio"), "fecha_inicio")
        assert_fecha_iso(body.get("fecha_fin"), "fecha_fin")
        assert date.fromisoformat(body["fecha_inicio"]) <= date.fromisoformat(
            body["fecha_fin"]
        ), "El rango por defecto debe estar ordenado cronologicamente"


# ---------------------------------------------------------------------------
# Balance de pedidos por estado (contrato §3).
# ---------------------------------------------------------------------------
class TestBalancePedidos:
    async def test_balance_incluye_los_cuatro_estados_y_total_coherente(
        self, make_client
    ):
        admin = await admin_session(make_client)
        response = await admin["client"].get(BALANCE, headers=admin["headers"])
        assert response.status_code == 200, response.text
        body = response.json()
        assert "balance" in body and "total_pedidos" in body

        balance = body["balance"]
        assert set(balance.keys()) == set(ESTADOS), (
            f"El balance debe traer exactamente los 4 estados: {balance}"
        )
        for estado in ESTADOS:
            assert_entero_no_negativo(balance[estado], f"balance[{estado}]")

        assert_entero_no_negativo(body["total_pedidos"], "total_pedidos")
        assert int(body["total_pedidos"]) == sum(
            int(balance[estado]) for estado in ESTADOS
        ), "El total debe ser la suma de los 4 estados"

    async def test_pedido_confirmado_aparece_en_registrado(self, make_client):
        pedido = await crear_pedido_confirmado(make_client)
        admin = await admin_session(make_client)
        response = await admin["client"].get(BALANCE, headers=admin["headers"])
        assert response.status_code == 200, response.text
        body = response.json()
        assert int(body["balance"]["Registrado"]) >= 1, (
            f"El pedido {pedido['numero']} recien confirmado debe contar en "
            f"'Registrado': {body}"
        )


# ---------------------------------------------------------------------------
# Inventario critico (contrato §4).
# ---------------------------------------------------------------------------
class TestInventarioCritico:
    async def test_estructura_e_invariantes_de_stock(self, make_client):
        admin = await admin_session(make_client)
        response = await admin["client"].get(CRITICO, headers=admin["headers"])
        assert response.status_code == 200, response.text
        body = response.json()

        for clave in ("stock_bajo", "quiebres", "mayor_rotacion"):
            assert clave in body, f"Falta la clave '{clave}': {body}"
            assert isinstance(body[clave], list), f"'{clave}' debe ser una lista"

        for item in body["stock_bajo"]:
            assert "producto_id" in item and "nombre" in item
            assert "stock_disponible" in item
            assert_entero_no_negativo(item["stock_disponible"], "stock_bajo.stock_disponible")
            assert int(item["stock_disponible"]) < 6, (
                "Todo producto en stock_bajo debe tener estrictamente < 6 unidades: "
                f"{item}"
            )

        for item in body["quiebres"]:
            assert "producto_id" in item and "nombre" in item
            assert int(item["stock_disponible"]) == 0, (
                f"Todo producto en quiebres debe tener stock 0: {item}"
            )

        for item in body["mayor_rotacion"]:
            assert "producto_id" in item and "nombre" in item
            assert "unidades_vendidas" in item
            assert_entero_no_negativo(
                item["unidades_vendidas"], "mayor_rotacion.unidades_vendidas"
            )
