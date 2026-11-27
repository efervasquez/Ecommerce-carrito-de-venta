"""Pruebas de caja negra para HU-08 (buzon de despacho y ciclo de vida de pedidos).

Escritas desde `contratos/CONTRATO-HU-08.md` v1 (aprobado), sin inspeccionar la
implementacion. Rutas, estados, roles, campos y textos se toman de la seccion
"Nombres que no se negocian" y de las tablas de comportamiento del contrato.

Los pedidos se generan con el flujo real de HU-07 (carrito autenticado + checkout
delivery + webhook `payment_intent.succeeded`), por lo que quedan en estado
`Registrado` con `zona_id` y `direccion_id`.

Nota de infraestructura: `tests/pytest.ini` fija el loop de los tests en scope
`session`, mientras que los fixtures async corren en un loop `function`. Por eso
todo el trabajo que toca BD/broker (login, pedidos, webhooks) se ejecuta dentro
del propio test mediante helpers, nunca dentro de un fixture async (misma leccion
que HU-05: evita "Future attached to a different loop").
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
import pymysql

# ---------------------------------------------------------------------------
# Semilla de usuarios RBAC (admin / motorizado) por variables de entorno.
# Se fijan antes de que `src.main` cargue la configuracion para que el seed del
# DEV (APP_ENV=test) cree los usuarios. Ver contrato: "Seed de usuarios
# admin/motorizado con credenciales por variables de entorno".
# ---------------------------------------------------------------------------
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SEED_RBAC_USERS", "true")

ADMIN_EMAIL = os.environ.setdefault("SEED_ADMIN_EMAIL", "hu08.admin@ejemplo.com")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "Admin12345!")
MOTORIZADO_EMAIL = os.environ.setdefault("SEED_MOTORIZADO_EMAIL", "hu08.motorizado@ejemplo.com")
os.environ.setdefault("SEED_MOTORIZADO_PASSWORD", "Moto12345!")

ADMIN_PASSWORD = os.environ["SEED_ADMIN_PASSWORD"]
MOTORIZADO_PASSWORD = os.environ["SEED_MOTORIZADO_PASSWORD"]

DESPACHO = "/api/v1/despacho"
PEDIDOS = f"{DESPACHO}/pedidos"
ZONAS = f"{DESPACHO}/zonas"
ASIGNACIONES = f"{DESPACHO}/asignaciones"
PENDIENTES = f"{DESPACHO}/pedidos/pendientes"

CHECKOUT = "/api/v1/checkout"
ZONAS_ENTREGA = "/api/v1/zonas"
DIRECCIONES = "/api/v1/direcciones"
WEBHOOK = "/api/v1/pagos/webhook"
PAGOS = "/api/v1/pagos"
CART_ITEMS = "/api/v1/carrito/items"
CATALOG = "/api/v1/catalogo/buscar"
REGISTRO = "/api/v1/auth/registro"
ACTIVAR = "/api/v1/auth/activar"
LOGIN = "/api/v1/auth/login"
QUEUE = "email.auth"

PASSWORD = "Password123!"
REGISTRADO = "Registrado"
PREPARANDO = "Preparando producto"
EN_CAMINO = "En camino"
ENTREGADO = "Entregado"

INVALID_TRANSITION_MESSAGE = (
    "Transición de estado inválida: el pedido debe pasar primero por "
    "'Preparando producto' y 'En camino'"
)
ORDER_NUMBER_RE = re.compile(r"^BL-\d+$")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_test")


def estado_url(numero: str) -> str:
    return f"{PEDIDOS}/{numero}/estado"


def auto_asignar_url(numero: str) -> str:
    return f"{PEDIDOS}/{numero}/auto-asignar"


def historial_url(numero: str) -> str:
    return f"{PEDIDOS}/{numero}/historial"


# ---------------------------------------------------------------------------
# Clientes con IP propia (evita el rate limit de auth compartido por IP).
# El fixture solo crea clientes; ninguna llamada a BD ocurre en el fixture.
# ---------------------------------------------------------------------------
@pytest.fixture
def make_client(app):
    """Crea clientes httpx DENTRO del loop del test (pytest-asyncio usa loop
    `session` para tests pero `function` para fixtures async: mezclarlos causa
    'Future attached to a different loop')."""

    def _make():
        import httpx
        from httpx import ASGITransport

        host = f"hu08-{uuid.uuid4().hex}"
        transport = ASGITransport(app=app, client=(host, 50000))
        return httpx.AsyncClient(transport=transport, base_url="http://testserver")

    return _make


@pytest.fixture(autouse=True)
def reset_shared_state(default_env):
    """Cada prueba parte de cero en carrito/pedidos/pagos/inventario.

    Se conservan `usuarios` y `zonas` (seed). Asi el buzón, los conteos por
    zona y la cola FIFO no dependen de pedidos creados por pruebas anteriores.
    """
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
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = DATABASE()"
            )
            existentes = {row[0] for row in cursor.fetchall()}
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            for table in (
                "pedido_estado_historial",
                "auditoria_receta_pendiente",
                "pagos",
                "pedido_items",
                "pedidos",
                "recetas",
                "carrito_items",
                "carritos",
                "direcciones",
                "inventario_stock",
            ):
                if table in existentes:
                    cursor.execute(f"DELETE FROM {table}")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
    finally:
        connection.close()
    yield


# ---------------------------------------------------------------------------
# Helpers de autenticacion (se invocan desde el test, en el loop correcto).
# ---------------------------------------------------------------------------
async def _rabbit_queue():
    """Mismo patron estable que test_hu01_auth._rabbit_queue."""
    import aio_pika

    url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()
    queue = await channel.declare_queue(QUEUE, durable=True)
    return connection, channel, queue


async def consume_activation_event(timeout: float = 10.0) -> dict:
    """Consume un unico mensaje de `email.auth` (patron HU-01)."""
    connection, channel, queue = await _rabbit_queue()
    try:
        async with queue.iterator(timeout=1) as iterator:
            message = await asyncio.wait_for(iterator.__anext__(), timeout=timeout)
            async with message.process():
                return json.loads(message.body)
    finally:
        await connection.close()


async def purge_activation_queue() -> None:
    """Purga inmediata antes de registrar (patron HU-01)."""
    connection, channel, queue = await _rabbit_queue()
    try:
        await queue.purge()
    finally:
        await connection.close()


async def register_and_get_token(client, email: str | None = None):
    await purge_activation_queue()
    email = email or f"hu08.{uuid.uuid4().hex[:12]}@ejemplo.com"
    response = await client.post(REGISTRO, json={"email": email})
    assert response.status_code == 200, (
        f"Registro esperaba 200, obtuvo {response.status_code}: {response.text}"
    )
    event = await consume_activation_event(timeout=10.0)
    return email, event


async def create_authenticated_headers(client) -> dict[str, str]:
    email, event = await register_and_get_token(client)
    activation = await client.post(
        ACTIVAR,
        json={"token": event["payload"]["token"], "password": PASSWORD},
    )
    assert activation.status_code == 200, activation.text
    login = await client.post(LOGIN, json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def login_seeded(client, email: str, password: str) -> tuple[dict[str, str], dict]:
    response = await client.post(LOGIN, json={"email": email, "password": password})
    assert response.status_code == 200, (
        f"El seed de usuarios RBAC no creo '{email}' (APP_ENV=test): {response.text}"
    )
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["usuario"]


async def admin_session(make_client) -> dict:
    client = make_client()
    headers, usuario = await login_seeded(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    return {"client": client, "headers": headers, "usuario": usuario}


async def motorizado_session(make_client) -> dict:
    client = make_client()
    headers, usuario = await login_seeded(client, MOTORIZADO_EMAIL, MOTORIZADO_PASSWORD)
    return {"client": client, "headers": headers, "usuario": usuario}


async def cliente_session(make_client) -> dict:
    client = make_client()
    headers = await create_authenticated_headers(client)
    return {"client": client, "headers": headers}


# ---------------------------------------------------------------------------
# Helpers de catalogo/carrito/webhook/pedidos.
# ---------------------------------------------------------------------------
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
    # El setup crea varios pedidos; elegir el de mayor stock evita caer en
    # `incidencia_stock` por agotamiento del producto en el propio setup.
    return max(products, key=lambda p: p.get("stock_disponible", 0))


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
                "status": "succeeded",
            }
        },
    }


async def post_webhook(client, event: dict):
    payload = json.dumps(event).encode()
    headers = {"Content-Type": "application/json"}
    headers.update(stripe_signature(payload))
    return await client.post(WEBHOOK, content=payload, headers=headers)


async def create_order(
    client, zone_index: int = 0, quantity: int = 1, headers: dict | None = None
) -> dict:
    """Crea un pedido `Registrado` por el flujo real de HU-07 en la zona indicada."""
    if headers is None:
        headers = await create_authenticated_headers(client)
    zones = await client.get(ZONAS_ENTREGA, headers=headers)
    assert zones.status_code == 200, zones.text
    zones_body = zones.json()
    assert zones_body, "El contrato HU-07 exige seed de al menos una zona activa"
    zone = zones_body[zone_index % len(zones_body)]

    address = await client.post(
        DIRECCIONES,
        json={
            "direccion_linea1": f"Av. Despacho {uuid.uuid4().hex[:6]}",
            "telefono_contacto": "999111222",
            "zona_id": zone["id"],
        },
        headers=headers,
    )
    assert address.status_code == 201, address.text

    product = await get_any_product(client)
    added = await client.post(
        CART_ITEMS,
        json={"producto_id": product["id"], "cantidad": quantity},
        headers=headers,
    )
    assert added.status_code == 200, added.text

    checkout = await client.post(
        CHECKOUT,
        json={"metodo_entrega": "delivery", "direccion_id": address.json()["id"]},
        headers=headers,
    )
    assert checkout.status_code == 200, checkout.text
    payment_intent_id = checkout.json()["payment_intent_id"]

    hook = await post_webhook(
        client, intent_event("payment_intent.succeeded", payment_intent_id)
    )
    assert hook.status_code == 200, hook.text

    status = await client.get(f"{PAGOS}/{payment_intent_id}", headers=headers)
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["pedido"] is not None, "El pago confirmado debe crear un pedido"
    pedido = status_body["pedido"]
    numero = pedido["numero"]
    assert ORDER_NUMBER_RE.match(numero), numero
    assert pedido["estado"] == REGISTRADO, (
        f"El pedido debe nacer en '{REGISTRADO}' para probar despacho, no en "
        f"'{pedido['estado']}' (posible incidencia de stock en el setup)"
    )
    return {"numero": numero, "zona_id": zone["id"], "zona": zone}


async def new_order(make_client, zone_index: int = 0, quantity: int = 1) -> dict:
    """Crea el pedido del setup; reintenta si el flujo HU-07 falla de forma transitoria.

    Las aserciones de despacho no cambian: esto solo estabiliza la creacion del
    pedido (auth, direccion, carrito y webhook) en una BD de test compartida.
    """
    ultimo_error = None
    for attempt in range(3):
        client = make_client()
        try:
            return await create_order(client, zone_index=zone_index, quantity=quantity)
        except AssertionError as error:
            ultimo_error = error
    raise ultimo_error


# ---------------------------------------------------------------------------
# Utilidades de lectura de respuestas (tolerantes a lista o envoltorio).
# ---------------------------------------------------------------------------
def extract_list(body) -> list:
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        for key in ("items", "pedidos", "pendientes", "data", "results", "zonas"):
            value = body.get(key)
            if isinstance(value, list):
                return value
    return []


def assert_domain_404(response) -> None:
    assert response.status_code == 404, response.text
    body = response.json()
    assert body.get("detail") != "Not Found", f"Endpoint no implementado: {response.text}"


async def list_pedidos(client, headers, **params) -> list[dict]:
    response = await client.get(PEDIDOS, headers=headers, params=params or None)
    assert response.status_code == 200, response.text
    return extract_list(response.json())


async def list_pendientes(client, headers, **params) -> list[dict]:
    response = await client.get(PENDIENTES, headers=headers, params=params or None)
    assert response.status_code == 200, response.text
    return extract_list(response.json())


def numeros(pedidos: list[dict]) -> list[str]:
    return [p["numero"] for p in pedidos]


async def preparar_pedido(
    make_client, admin: dict, motorizado: dict, zone_index: int = 0
) -> dict:
    """Crea un pedido y lo deja en `Preparando producto` asignado al motorizado."""
    order = await new_order(make_client, zone_index=zone_index)
    response = await admin["client"].post(
        ASIGNACIONES,
        json={
            "zona_id": order["zona_id"],
            "pedido_numeros": [order["numero"]],
            "motorizado_id": motorizado["usuario"]["id"],
        },
        headers=admin["headers"],
    )
    assert response.status_code == 200, (
        f"Asignacion rechazada. pedido={order} motorizado_id={motorizado['usuario']['id']} "
        f"respuesta={response.text}"
    )
    return order


# ---------------------------------------------------------------------------
# RBAC y sesion.
# ---------------------------------------------------------------------------
class TestRBAC:
    ENDPOINTS = [
        ("GET", PEDIDOS, None),
        ("GET", ZONAS, None),
        ("POST", ASIGNACIONES, {"zona_id": 1, "pedido_numeros": ["BL-1"], "motorizado_id": 1}),
        ("GET", PENDIENTES, None),
        ("POST", auto_asignar_url("BL-1"), None),
        ("PATCH", estado_url("BL-1"), {"estado": EN_CAMINO}),
        ("GET", historial_url("BL-1"), None),
    ]

    @pytest.mark.parametrize("method,url,body", ENDPOINTS)
    async def test_sin_sesion_retorna_401(self, make_client, method, url, body):
        client = make_client()
        response = await client.request(method, url, json=body)
        assert response.status_code == 401, response.text

    @pytest.mark.parametrize("method,url,body", ENDPOINTS)
    async def test_rol_cliente_retorna_403(self, make_client, method, url, body):
        cliente = await cliente_session(make_client)
        response = await cliente["client"].request(
            method, url, json=body, headers=cliente["headers"]
        )
        assert response.status_code == 403, response.text

    async def test_admin_puede_leer_buzon_y_zonas(self, make_client):
        admin = await admin_session(make_client)
        buzon = await admin["client"].get(PEDIDOS, headers=admin["headers"])
        assert buzon.status_code == 200, buzon.text
        zonas = await admin["client"].get(ZONAS, headers=admin["headers"])
        assert zonas.status_code == 200, zonas.text

    async def test_motorizado_no_puede_asignar_lotes(self, make_client):
        order = await new_order(make_client)
        motorizado = await motorizado_session(make_client)
        response = await motorizado["client"].post(
            ASIGNACIONES,
            json={
                "zona_id": order["zona_id"],
                "pedido_numeros": [order["numero"]],
                "motorizado_id": motorizado["usuario"]["id"],
            },
            headers=motorizado["headers"],
        )
        assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# Buzon y consolidacion por zona.
# ---------------------------------------------------------------------------
class TestBuzon:
    async def test_buzon_lista_pedidos_registrados_con_campos_del_contrato(
        self, make_client
    ):
        order = await new_order(make_client)
        admin = await admin_session(make_client)
        pedidos = await list_pedidos(admin["client"], admin["headers"], estado=REGISTRADO)
        assert numeros(pedidos), "El buzon debe listar pedidos"
        assert order["numero"] in numeros(pedidos)

        registro = next(p for p in pedidos if p["numero"] == order["numero"])
        for campo in (
            "numero",
            "estado",
            "zona_id",
            "distrito",
            "metodo_entrega",
            "motorizado_id",
            "monto",
            "creado_en",
        ):
            assert campo in registro, f"Falta el campo '{campo}' en el buzon"
        assert registro["estado"] == REGISTRADO
        assert registro["zona_id"] == order["zona_id"]

    async def test_buzon_filtra_por_zona(self, make_client):
        order = await new_order(make_client, zone_index=0)
        admin = await admin_session(make_client)
        pedidos = await list_pedidos(
            admin["client"], admin["headers"], zona_id=order["zona_id"]
        )
        assert all(p["zona_id"] == order["zona_id"] for p in pedidos)
        assert order["numero"] in numeros(pedidos)

    async def test_zonas_expone_conteos_por_estado(self, make_client):
        first = await new_order(make_client, zone_index=0)
        await new_order(make_client, zone_index=0)
        admin = await admin_session(make_client)
        response = await admin["client"].get(ZONAS, headers=admin["headers"])
        assert response.status_code == 200, response.text
        zonas = extract_list(response.json())
        entry = next((z for z in zonas if z.get("zona_id") == first["zona_id"]), None)
        assert entry is not None, "La consolidacion debe incluir la zona de los pedidos"
        for campo in (
            "zona_id",
            "nombre",
            "distrito",
            "pedidos_registrados",
            "pedidos_preparando",
            "pedidos_en_camino",
            "pedidos_entregados",
        ):
            assert campo in entry, f"Falta el campo '{campo}' en consolidacion por zona"
        assert entry["pedidos_registrados"] >= 2


# ---------------------------------------------------------------------------
# Asignacion a motorizado (admin).
# ---------------------------------------------------------------------------
class TestAsignacion:
    async def test_asignacion_valida_pasa_lote_a_preparando(self, make_client):
        first = await new_order(make_client, zone_index=0)
        second = await new_order(make_client, zone_index=0)
        admin = await admin_session(make_client)
        motorizado = await motorizado_session(make_client)
        response = await admin["client"].post(
            ASIGNACIONES,
            json={
                "zona_id": first["zona_id"],
                "pedido_numeros": [first["numero"], second["numero"]],
                "motorizado_id": motorizado["usuario"]["id"],
            },
            headers=admin["headers"],
        )
        assert response.status_code == 200, response.text

        preparando = await list_pedidos(
            admin["client"], admin["headers"], estado=PREPARANDO, zona_id=first["zona_id"]
        )
        por_numero = {p["numero"]: p for p in preparando}
        for order in (first, second):
            assert order["numero"] in por_numero
            assert por_numero[order["numero"]]["motorizado_id"] == motorizado["usuario"]["id"]

    async def test_asignacion_no_parcial_con_estados_mezclados(self, make_client):
        first = await new_order(make_client, zone_index=0)
        second = await new_order(make_client, zone_index=0)
        admin = await admin_session(make_client)
        motorizado = await motorizado_session(make_client)

        ready = await admin["client"].post(
            ASIGNACIONES,
            json={
                "zona_id": first["zona_id"],
                "pedido_numeros": [first["numero"]],
                "motorizado_id": motorizado["usuario"]["id"],
            },
            headers=admin["headers"],
        )
        assert ready.status_code == 200, ready.text

        mixed = await admin["client"].post(
            ASIGNACIONES,
            json={
                "zona_id": first["zona_id"],
                "pedido_numeros": [first["numero"], second["numero"]],
                "motorizado_id": motorizado["usuario"]["id"],
            },
            headers=admin["headers"],
        )
        assert mixed.status_code == 409, mixed.text

        registrados = await list_pedidos(
            admin["client"], admin["headers"], estado=REGISTRADO, zona_id=first["zona_id"]
        )
        assert second["numero"] in numeros(registrados), "No debe asignarse parcialmente"

    async def test_asignacion_no_parcial_con_zonas_mezcladas(self, make_client):
        first = await new_order(make_client, zone_index=0)
        second = await new_order(make_client, zone_index=1)
        if second["zona_id"] == first["zona_id"]:
            pytest.skip("El seed solo expone una zona activa; no hay mezcla de zonas posible")

        admin = await admin_session(make_client)
        motorizado = await motorizado_session(make_client)
        mixed = await admin["client"].post(
            ASIGNACIONES,
            json={
                "zona_id": first["zona_id"],
                "pedido_numeros": [first["numero"], second["numero"]],
                "motorizado_id": motorizado["usuario"]["id"],
            },
            headers=admin["headers"],
        )
        assert mixed.status_code == 409, mixed.text

        registrados = await list_pedidos(
            admin["client"], admin["headers"], estado=REGISTRADO
        )
        assert second["numero"] in numeros(registrados)

    async def test_motorizado_id_invalido_retorna_422_o_404(self, make_client):
        order = await new_order(make_client, zone_index=0)
        admin = await admin_session(make_client)
        response = await admin["client"].post(
            ASIGNACIONES,
            json={
                "zona_id": order["zona_id"],
                "pedido_numeros": [order["numero"]],
                "motorizado_id": 987654321,
            },
            headers=admin["headers"],
        )
        assert response.status_code in (404, 422), response.text
        if response.status_code == 404:
            assert_domain_404(response)


# ---------------------------------------------------------------------------
# Auto-asignacion FIFO (motorizado).
# ---------------------------------------------------------------------------
class TestAutoAsignacion:
    async def test_pendientes_orden_fifo_por_llegada(self, make_client):
        first = await new_order(make_client, zone_index=0)
        await asyncio.sleep(1.05)
        second = await new_order(make_client, zone_index=0)
        await asyncio.sleep(1.05)
        third = await new_order(make_client, zone_index=0)
        motorizado = await motorizado_session(make_client)

        pendientes = await list_pendientes(
            motorizado["client"], motorizado["headers"], zona_id=first["zona_id"]
        )
        assert all(p["estado"] == REGISTRADO for p in pendientes), pendientes
        assert all(p["zona_id"] == first["zona_id"] for p in pendientes), pendientes

        # La BD de test acumula pedidos de otras corridas; lo verificable es que
        # MIS tres pedidos aparezcan y en orden de llegada (FIFO) entre ellos.
        posiciones = {
            numero: index
            for index, numero in enumerate(numeros(pendientes))
            if numero in (first["numero"], second["numero"], third["numero"])
        }
        assert set(posiciones) == {
            first["numero"],
            second["numero"],
            third["numero"],
        }, f"Faltan pedidos propios en pendientes: {pendientes}"
        assert posiciones[first["numero"]] < posiciones[second["numero"]] < posiciones[third["numero"]], (
            f"Los pendientes no respetan el orden de llegada: {numeros(pendientes)}"
        )

    async def test_auto_asignar_toma_el_mas_antiguo_y_rechaza_saltarse_la_fila(
        self, make_client
    ):
        first = await new_order(make_client, zone_index=0)
        await asyncio.sleep(1.05)
        await new_order(make_client, zone_index=0)
        motorizado = await motorizado_session(make_client)

        pendientes = await list_pendientes(
            motorizado["client"], motorizado["headers"], zona_id=first["zona_id"]
        )
        # Los pedidos `retiro` no entran en el reparto a domicilio; solo se
        # auto-asignan los de entrega `delivery` (contrato HU-07/HU-08).
        elegibles = [p for p in pendientes if p.get("metodo_entrega") == "delivery"]
        assert len(elegibles) >= 2, f"Se requieren dos pendientes delivery: {pendientes}"
        oldest = elegibles[0]["numero"]
        not_oldest = elegibles[-1]["numero"]
        assert oldest != not_oldest

        skipped = await motorizado["client"].post(
            auto_asignar_url(not_oldest), headers=motorizado["headers"]
        )
        assert skipped.status_code == 409, (
            f"Saltarse la fila FIFO debe dar 409; numero={not_oldest} respuesta={skipped.text}"
        )

        assigned = await motorizado["client"].post(
            auto_asignar_url(oldest), headers=motorizado["headers"]
        )
        assert assigned.status_code == 200, (
            f"Auto-asignar el mas antiguo debe dar 200; numero={oldest} "
            f"respuesta={assigned.text}"
        )

        preparando = await list_pedidos(
            motorizado["client"],
            motorizado["headers"],
            estado=PREPARANDO,
            zona_id=first["zona_id"],
        )
        registro = next(p for p in preparando if p["numero"] == oldest)
        assert registro["motorizado_id"] == motorizado["usuario"]["id"]

        restantes = await list_pendientes(
            motorizado["client"], motorizado["headers"], zona_id=first["zona_id"]
        )
        assert oldest not in numeros(restantes)
        assert not_oldest in numeros(restantes)


# ---------------------------------------------------------------------------
# Ciclo de vida de 4 estados.
# ---------------------------------------------------------------------------
class TestCicloVida:
    async def test_recorrido_preparando_en_camino_entregado(self, make_client):
        admin = await admin_session(make_client)
        motorizado = await motorizado_session(make_client)
        order = await preparar_pedido(make_client, admin, motorizado)

        to_on_way = await motorizado["client"].patch(
            estado_url(order["numero"]),
            json={"estado": EN_CAMINO},
            headers=motorizado["headers"],
        )
        assert to_on_way.status_code == 200, to_on_way.text

        en_camino = await list_pedidos(
            admin["client"], admin["headers"], estado=EN_CAMINO, zona_id=order["zona_id"]
        )
        assert order["numero"] in numeros(en_camino)

        delivered = await motorizado["client"].patch(
            estado_url(order["numero"]),
            json={"estado": ENTREGADO},
            headers=motorizado["headers"],
        )
        assert delivered.status_code == 200, delivered.text

        entregados = await list_pedidos(
            admin["client"], admin["headers"], estado=ENTREGADO, zona_id=order["zona_id"]
        )
        assert order["numero"] in numeros(entregados)

    async def test_salto_invalido_retorna_409_con_mensaje_exacto(self, make_client):
        admin = await admin_session(make_client)
        motorizado = await motorizado_session(make_client)
        order = await preparar_pedido(make_client, admin, motorizado)

        response = await motorizado["client"].patch(
            estado_url(order["numero"]),
            json={"estado": ENTREGADO},
            headers=motorizado["headers"],
        )
        assert response.status_code == 409, response.text
        assert response.json()["detail"] == INVALID_TRANSITION_MESSAGE

        preparando = await list_pedidos(
            admin["client"], admin["headers"], estado=PREPARANDO, zona_id=order["zona_id"]
        )
        assert order["numero"] in numeros(preparando), "El estado invalido no debe cambiar"

    @pytest.mark.skip(
        reason="NO VERIFICADO: el seed solo crea un motorizado, por lo que no es posible "
        "producir un pedido en Preparando asignado a OTRO motorizado. Con un pedido en "
        "Registrado ambos casos se solapan (salto invalido -> 409 segun maquina de estados). "
        "El 403 por rol cliente ya se cubre en TestRBAC."
    )
    async def test_pedido_de_otro_motorizado_retorna_403(self, make_client):
        ...


# ---------------------------------------------------------------------------
# Auditoria de estados.
# ---------------------------------------------------------------------------
class TestHistorial:
    async def test_historial_registra_transiciones_usuario_y_tiempo(self, make_client):
        admin = await admin_session(make_client)
        motorizado = await motorizado_session(make_client)
        order = await preparar_pedido(make_client, admin, motorizado)
        for target in (EN_CAMINO, ENTREGADO):
            response = await motorizado["client"].patch(
                estado_url(order["numero"]),
                json={"estado": target},
                headers=motorizado["headers"],
            )
            assert response.status_code == 200, response.text

        response = await admin["client"].get(
            historial_url(order["numero"]), headers=admin["headers"]
        )
        assert response.status_code == 200, response.text
        historial = extract_list(response.json())
        assert len(historial) >= 3, historial

        transiciones = [(h["estado_anterior"], h["estado_nuevo"]) for h in historial]
        assert transiciones[0] == (REGISTRADO, PREPARANDO)
        assert (PREPARANDO, EN_CAMINO) in transiciones
        assert (EN_CAMINO, ENTREGADO) in transiciones

        for entry in historial:
            assert entry["usuario_id"] is not None
            assert entry["timestamp"]

        timestamps = [h["timestamp"] for h in historial]
        assert timestamps == sorted(timestamps), "El historial debe ser cronologico"

    async def test_historial_pedido_inexistente_retorna_404(self, make_client):
        admin = await admin_session(make_client)
        response = await admin["client"].get(
            historial_url("BL-999999"), headers=admin["headers"]
        )
        assert_domain_404(response)


# ---------------------------------------------------------------------------
# Fuera del flujo de 4 estados.
# ---------------------------------------------------------------------------
class TestNoVerificado:
    @pytest.mark.skip(
        reason="NO VERIFICADO (contrato, decision 4): provocar `incidencia_stock` exige "
        "una inconsistencia fisica de stock no observable en caja negra; HU-07 ya lo "
        "marca NO VERIFICADO."
    )
    async def test_incidencia_stock_no_transiciona(self, make_client):
        ...
