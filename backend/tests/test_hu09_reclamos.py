"""Pruebas de caja negra para HU-09 (reclamos, logistica inversa y cero reembolsos).

Escritas desde `contratos/CONTRATO-HU-09.md` v2 (aprobado), sin inspeccionar la
implementacion. Rutas, estados, roles, campos y textos se toman de la seccion
"Nombres que no se negocian" y de las tablas de comportamiento del contrato.

Los pedidos se generan con el flujo real de HU-07 (carrito autenticado + checkout
delivery + webhook `payment_intent.succeeded`) y se llevan a `Entregado` con el
ciclo de vida de HU-08 (asignacion por admin + transiciones del motorizado).

Nota de infraestructura: `tests/pytest.ini` fija el loop de los tests en scope
`session`, mientras que los fixtures async corren en un loop `function`. Por eso
todo el trabajo que toca BD/broker (login, pedidos, reclamos) se ejecuta dentro
del propio test mediante helpers, nunca dentro de un fixture async.
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
# Mismo patron que test_hu08_despacho: se fijan antes de que `src.main` cargue la
# configuracion para que el seed del DEV (APP_ENV=test) cree los usuarios.
# `setdefault` respeta los valores ya fijados por otros modulos de la sesion.
# ---------------------------------------------------------------------------
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SEED_RBAC_USERS", "true")

ADMIN_EMAIL = os.environ.setdefault("SEED_ADMIN_EMAIL", "hu09.admin@ejemplo.com")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "Admin12345!")
MOTORIZADO_EMAIL = os.environ.setdefault("SEED_MOTORIZADO_EMAIL", "hu09.motorizado@ejemplo.com")
os.environ.setdefault("SEED_MOTORIZADO_PASSWORD", "Moto12345!")

ADMIN_PASSWORD = os.environ["SEED_ADMIN_PASSWORD"]
MOTORIZADO_PASSWORD = os.environ["SEED_MOTORIZADO_PASSWORD"]

RECLAMOS = "/api/v1/reclamos"
PEDIDOS = "/api/v1/pedidos"
DESPACHO_PEDIDOS = "/api/v1/despacho/pedidos"
ASIGNACIONES = "/api/v1/despacho/asignaciones"
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
ENTREGADO = "Entregado"
EN_CAMINO = "En camino"

APROBADO = "aprobado"
REINTENTO = "reintento_pendiente"
CERRADO = "cerrado_exitoso"
ESCALADO = "escalado_supervision"

MSG_FALTA_FOTO_PRODUCTO = "La fotografía del producto dañado es obligatoria."
MSG_FALTA_COMPROBANTE = (
    "La fotografía o archivo del comprobante de pago es obligatoria."
)
MSG_FORMATO = "Formato de archivo no soportado. Debe ser JPG, PNG o PDF."
MSG_NO_ENTREGADO = (
    "Solo se pueden registrar reclamos para pedidos con estado Entregado."
)
MSG_PEDIDO_AJENO = "Pedido no encontrado o no pertenece al usuario autenticado."
MSG_PRODUCTO_AJENO = (
    "El producto indicado no pertenece a los ítems del pedido original."
)
MSG_ARRERPENTIMIENTO = (
    "No proceden reclamos por arrepentimiento o error en la compra. Solo aplica "
    "para productos dañados o en mal estado."
)
MSG_CONFORMIDAD_INCOMPLETA = (
    "Para dar conformidad se deben validar físicamente los 3 requisitos: "
    "comprobante original, pertenencia a Botica la Luz y defecto físico."
)
MSG_FALLA_SIN_MOTIVO = (
    "El motivo de la falla es requerido cuando la inspección no es conforme."
)
MSG_CERRADO_EXITOSO = "Cambio físico completado con éxito."
MSG_REINTENTO = (
    "Intento fallido registrado. Se permite reprogramar nuevo intento de cambio."
)
MSG_ESCALADO = (
    "Límite de 3 intentos adicionales alcanzado. Reclamo escalado a supervisión."
)
MSG_ESTADO_FINAL = (
    "El reclamo ya no admite inspecciones en campo (estado final alcanzado)."
)
MSG_ROL_INSPECCION = (
    "Solo el personal de reparto o administración puede registrar inspecciones en campo."
)
MSG_CERO_REEMBOLSOS = (
    "Política estricta de cero reembolsos: la botica no realiza devoluciones de "
    "dinero ni extornos."
)
MSG_ACCION_NO_PERMITIDA = (
    "Acción no permitida: política estricta de reposición física sin reembolso "
    "monetario."
)

ORDER_NUMBER_RE = re.compile(r"^BL-\d+$")
REPOSICION_RE = re.compile(r"^BL-REP-")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_test")


# ---------------------------------------------------------------------------
# Clientes con IP propia (evita el rate limit de auth compartido por IP).
# El fixture solo crea clientes; ninguna llamada a BD ocurre en el fixture.
# ---------------------------------------------------------------------------
@pytest.fixture
def make_client(app):
    def _make():
        import httpx
        from httpx import ASGITransport

        host = f"hu09-{uuid.uuid4().hex}"
        transport = ASGITransport(app=app, client=(host, 50000))
        return httpx.AsyncClient(transport=transport, base_url="http://testserver")

    return _make


@pytest.fixture(autouse=True)
def reset_shared_state(default_env):
    """Cada prueba parte de cero en reclamos, pedidos, pagos e inventario.

    Se conservan `usuarios` y `zonas` (seed). Las tablas de reclamos se detectan
    por nombre para no acoplarse a los nombres internos que elija el DEV.
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
            conocidas = {
                "reclamos",
                "reclamo",
                "reclamo_inspeccion",
                "reclamo_inspecciones",
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
            }
            candidatas = existentes & conocidas
            candidatas |= {
                table
                for table in existentes
                if "reclamo" in table.lower() or "merma" in table.lower()
            }
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            for table in candidatas:
                cursor.execute(f"DELETE FROM {table}")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
    finally:
        connection.close()
    yield


# ---------------------------------------------------------------------------
# Helpers de autenticacion (se invocan desde el test, en el loop correcto).
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


async def create_authenticated_headers(client) -> dict[str, str]:
    await purge_activation_queue()
    email = f"hu09.{uuid.uuid4().hex[:12]}@ejemplo.com"
    response = await client.post(REGISTRO, json={"email": email})
    assert response.status_code == 200, (
        f"Registro esperaba 200, obtuvo {response.status_code}: {response.text}"
    )
    event = await consume_activation_event(timeout=10.0)
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


# ---------------------------------------------------------------------------
# Helpers de catalogo / pedidos / webhook.
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


async def create_order(client, headers: dict | None = None) -> dict:
    """Crea un pedido `Registrado` por el flujo real de HU-07 (entrega delivery)."""
    if headers is None:
        headers = await create_authenticated_headers(client)
    zones = await client.get(ZONAS_ENTREGA, headers=headers)
    assert zones.status_code == 200, zones.text
    zones_body = zones.json()
    assert zones_body, "El contrato HU-07 exige seed de al menos una zona activa"
    zone = zones_body[0]

    address = await client.post(
        DIRECCIONES,
        json={
            "direccion_linea1": f"Av. Reclamos {uuid.uuid4().hex[:6]}",
            "telefono_contacto": "999111222",
            "zona_id": zone["id"],
        },
        headers=headers,
    )
    assert address.status_code == 201, address.text

    product = await get_any_product(client)
    added = await client.post(
        CART_ITEMS,
        json={"producto_id": product["id"], "cantidad": 1},
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
    numero = status_body["pedido"]["numero"]
    assert ORDER_NUMBER_RE.match(numero), numero
    assert status_body["pedido"]["estado"] == REGISTRADO, (
        "El pedido debe nacer en 'Registrado' (posible incidencia de stock en el setup)"
    )

    detail = await client.get(f"{PEDIDOS}/{numero}", headers=headers)
    assert detail.status_code == 200, detail.text
    items = detail.json()["items"]
    assert items, "El pedido debe tener items para poder reclamar por producto"
    return {
        "numero": numero,
        "zona_id": zone["id"],
        "producto_id": items[0]["producto_id"],
        "items": items,
        "monto": detail.json().get("monto"),
        "client": client,
        "headers": headers,
    }


async def delivered_order(make_client) -> dict:
    """Crea el pedido del cliente y lo deja en `Entregado` por el ciclo HU-08."""
    for attempt in range(3):
        client = make_client()
        headers = await create_authenticated_headers(client)
        try:
            order = await create_order(client, headers=headers)
            break
        except AssertionError:
            if attempt == 2:
                raise
    else:  # pragma: no cover - defensivo
        raise AssertionError("No se pudo crear el pedido de setup")

    admin = await admin_session(make_client)
    motorizado = await motorizado_session(make_client)
    assigned = await admin["client"].post(
        ASIGNACIONES,
        json={
            "zona_id": order["zona_id"],
            "pedido_numeros": [order["numero"]],
            "motorizado_id": motorizado["usuario"]["id"],
        },
        headers=admin["headers"],
    )
    assert assigned.status_code == 200, assigned.text

    for estado in (EN_CAMINO, ENTREGADO):
        transition = await motorizado["client"].patch(
            f"{DESPACHO_PEDIDOS}/{order['numero']}/estado",
            json={"estado": estado},
            headers=motorizado["headers"],
        )
        assert transition.status_code == 200, transition.text

    order["motorizado"] = motorizado
    order["admin"] = admin
    return order


# ---------------------------------------------------------------------------
# Helpers de evidencias / reclamos.
# ---------------------------------------------------------------------------
def archivo_jpg(nombre: str = "producto.jpg") -> tuple[str, bytes, str]:
    return (nombre, b"\xff\xd8\xff\xe0" + b"evidencia" * 8, "image/jpeg")


def archivo_pdf(nombre: str = "comprobante.pdf") -> tuple[str, bytes, str]:
    return (nombre, b"%PDF-1.4\n%comprobante", "application/pdf")


def reclamo_data(order: dict, producto_id: int | None = None, motivo: str = "Producto dañado") -> dict:
    return {
        "pedido_numero": order["numero"],
        "producto_id": str(order["producto_id"] if producto_id is None else producto_id),
        "motivo": motivo,
        "descripcion": "Frasco quebrado al abrir el empaque",
    }


async def registrar_reclamo(
    order: dict,
    *,
    producto_id: int | None = None,
    motivo: str = "Producto dañado",
    foto_producto: tuple | None = None,
    foto_comprobante: tuple | None = None,
    datos_extra: dict | None = None,
):
    data = reclamo_data(order, producto_id=producto_id, motivo=motivo)
    if datos_extra:
        data.update(datos_extra)
    files = {}
    if foto_producto is not False:
        files["foto_producto"] = foto_producto or archivo_jpg()
    if foto_comprobante is not False:
        files["foto_comprobante"] = foto_comprobante or archivo_pdf()
    return await order["client"].post(
        RECLAMOS, data=data, files=files, headers=order["headers"]
    )


async def reclamo_aprobado(make_client) -> tuple[dict, dict]:
    order = await delivered_order(make_client)
    response = await registrar_reclamo(order)
    assert response.status_code == 201, response.text
    return order, response.json()


def inspeccion_body(resultado: str = "conforme", **overrides) -> dict:
    body = {
        "resultado": resultado,
        "comprobante_verificado": resultado == "conforme",
        "pertenencia_botica_verificada": resultado == "conforme",
        "defecto_fisico_verificado": resultado == "conforme",
    }
    if resultado != "conforme":
        body["motivo_falla"] = "El producto no cumple los requisitos"
    body.update(overrides)
    return body


async def inspeccionar(order: dict, reclamo_id: int, body: dict | None = None, session: dict | None = None):
    actor = session or order["motorizado"]
    return await actor["client"].post(
        f"{RECLAMOS}/{reclamo_id}/inspeccion-campo",
        json=body or inspeccion_body(),
        headers=actor["headers"],
    )


def extract_list(body) -> list:
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        for key in ("items", "reclamos", "data", "results"):
            value = body.get(key)
            if isinstance(value, list):
                return value
    return []


CAMPOS_ITEM_LISTA = (
    "id",
    "pedido_origen_numero",
    "pedido_reposicion_numero",
    "producto_id",
    "estado",
    "intentos_adicionales_realizados",
    "creado_en",
)


def assert_estructura_listado(body) -> list:
    """Valida el esquema de ítem del listado definido en el contrato v2."""
    items = extract_list(body)
    for item in items:
        assert isinstance(item, dict), f"Ítem de listado inválido: {item!r}"
        for campo in CAMPOS_ITEM_LISTA:
            assert campo in item, (
                f"Falta el campo '{campo}' en el ítem del listado: {item}"
            )
        assert item["estado"] in {APROBADO, REINTENTO, CERRADO, ESCALADO}, item
    return items


def assert_domain_404(response) -> None:
    assert response.status_code == 404, response.text
    assert response.json().get("detail") != "Not Found", (
        f"Endpoint no implementado: {response.text}"
    )


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


# ---------------------------------------------------------------------------
# RBAC y sesion (contrato §1).
# ---------------------------------------------------------------------------
class TestRBAC:
    ENDPOINTS = [
        ("GET", RECLAMOS, {"json": None}),
        ("GET", f"{RECLAMOS}/1", {"json": None}),
        (
            "POST",
            RECLAMOS,
            {
                "data": {
                    "pedido_numero": "BL-1",
                    "producto_id": "1",
                    "motivo": "Producto dañado",
                }
            },
        ),
        ("POST", f"{RECLAMOS}/1/inspeccion-campo", {"json": {"resultado": "conforme"}}),
        ("POST", f"{RECLAMOS}/1/reembolso", {"json": None}),
    ]

    @pytest.mark.parametrize("method,url,kwargs", ENDPOINTS)
    async def test_sin_sesion_retorna_401(self, make_client, method, url, kwargs):
        client = make_client()
        response = await client.request(method, url, **kwargs)
        assert response.status_code == 401, (
            f"{method} {url} sin JWT debe dar 401, obtuvo {response.status_code}: "
            f"{response.text}"
        )

    async def test_cliente_no_puede_registrar_inspeccion_en_campo(self, make_client):
        _, reclamo = await reclamo_aprobado(make_client)
        client = make_client()
        headers = await create_authenticated_headers(client)
        response = await client.post(
            f"{RECLAMOS}/{reclamo['id']}/inspeccion-campo",
            json=inspeccion_body(),
            headers=headers,
        )
        assert response.status_code == 403, response.text
        assert response.json()["detail"] == MSG_ROL_INSPECCION


# ---------------------------------------------------------------------------
# Registro obligatorio del reclamo con evidencias (contrato §2).
# ---------------------------------------------------------------------------
class TestRegistro:
    async def test_camino_feliz_crea_reclamo_y_pedido_de_reposicion(self, make_client):
        order = await delivered_order(make_client)
        antes = stock_row(order["producto_id"])
        assert antes is not None, "El pedido entregado debe dejar fila de inventario"

        response = await registrar_reclamo(order)
        assert response.status_code == 201, response.text
        body = response.json()

        assert body["id"]
        assert body["pedido_origen_numero"] == order["numero"]
        assert body["producto_id"] == order["producto_id"]
        assert body["estado"] == APROBADO
        assert body["intentos_adicionales_realizados"] == 0
        assert body["creado_en"]

        reposicion_numero = body["pedido_reposicion_numero"]
        assert REPOSICION_RE.match(reposicion_numero), (
            f"El pedido de reposicion debe llevar prefijo BL-REP-: {reposicion_numero}"
        )

        detalle = await order["client"].get(
            f"{RECLAMOS}/{body['id']}", headers=order["headers"]
        )
        assert detalle.status_code == 200, detalle.text
        detalle_body = detalle.json()
        assert detalle_body["id"] == body["id"]
        assert detalle_body["estado"] == APROBADO

        reposicion = await order["client"].get(
            f"{PEDIDOS}/{reposicion_numero}", headers=order["headers"]
        )
        assert reposicion.status_code == 200, reposicion.text
        reposicion_body = reposicion.json()
        assert reposicion_body["estado"] == REGISTRADO, (
            "El pedido de reposicion debe nacer en 'Registrado'"
        )
        assert float(reposicion_body["monto"]) == 0.0, (
            "El pedido de reposicion no debe tener costo para el cliente"
        )
        assert reposicion_body["moneda"] == "PEN"
        assert reposicion_body["metodo_entrega"] == "delivery"
        assert {item["producto_id"] for item in reposicion_body["items"]} == {
            order["producto_id"]
        }
        if "tipo" in reposicion_body:
            assert reposicion_body["tipo"] == "reposicion"

        despues = stock_row(order["producto_id"])
        assert despues is not None
        comprometido = (antes[0] - despues[0]) + (despues[1] - antes[1])
        assert comprometido == 1, (
            "El reclamo debe reservar/descontar exactamente 1 unidad de stock de "
            f"reemplazo. antes={antes} despues={despues}"
        )

    async def test_falta_foto_producto_retorna_422(self, make_client):
        order = await delivered_order(make_client)
        response = await registrar_reclamo(order, foto_producto=False)
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_FALTA_FOTO_PRODUCTO

    async def test_falta_foto_comprobante_retorna_422(self, make_client):
        order = await delivered_order(make_client)
        response = await registrar_reclamo(order, foto_comprobante=False)
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_FALTA_COMPROBANTE

    @pytest.mark.parametrize("campo", ["foto_producto", "foto_comprobante"])
    async def test_formato_de_archivo_invalido_retorna_422(self, make_client, campo):
        order = await delivered_order(make_client)
        invalido = ("evidencia.txt", b"no es imagen", "text/plain")
        response = await registrar_reclamo(order, **{campo: invalido})
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_FORMATO

    async def test_pedido_no_entregado_retorna_409(self, make_client):
        client = make_client()
        headers = await create_authenticated_headers(client)
        order = await create_order(client, headers=headers)
        response = await registrar_reclamo(order)
        assert response.status_code == 409, response.text
        assert response.json()["detail"] == MSG_NO_ENTREGADO

    async def test_pedido_de_otro_cliente_retorna_404(self, make_client):
        order = await delivered_order(make_client)
        intruso = make_client()
        headers = await create_authenticated_headers(intruso)
        data = reclamo_data(order)
        response = await intruso.post(
            RECLAMOS,
            data=data,
            files={"foto_producto": archivo_jpg(), "foto_comprobante": archivo_pdf()},
            headers=headers,
        )
        assert response.status_code == 404, response.text
        assert response.json()["detail"] == MSG_PEDIDO_AJENO

    async def test_pedido_inexistente_retorna_404(self, make_client):
        client = make_client()
        headers = await create_authenticated_headers(client)
        data = {
            "pedido_numero": "BL-999999",
            "producto_id": "1",
            "motivo": "Producto dañado",
        }
        response = await client.post(
            RECLAMOS,
            data=data,
            files={"foto_producto": archivo_jpg(), "foto_comprobante": archivo_pdf()},
            headers=headers,
        )
        assert response.status_code == 404, response.text
        assert response.json()["detail"] == MSG_PEDIDO_AJENO

    async def test_producto_que_no_pertenece_al_pedido_retorna_422(self, make_client):
        order = await delivered_order(make_client)
        ajeno = order["producto_id"] + 900000
        response = await registrar_reclamo(order, producto_id=ajeno)
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_PRODUCTO_AJENO

    @pytest.mark.parametrize(
        "motivo",
        [
            "Me arrepentí de la compra",
            "Fue un error en la compra",
            "Quiero devolverlo porque ya no lo necesito",
        ],
    )
    async def test_motivo_de_arrepentimiento_retorna_422(self, make_client, motivo):
        order = await delivered_order(make_client)
        response = await registrar_reclamo(order, motivo=motivo)
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_ARRERPENTIMIENTO


# ---------------------------------------------------------------------------
# Validacion fisica en campo (contrato §4).
# ---------------------------------------------------------------------------
class TestInspeccionCampo:
    async def test_conforme_completa_cambio_y_entrega_reposicion(self, make_client):
        order, reclamo = await reclamo_aprobado(make_client)
        response = await inspeccionar(order, reclamo["id"])
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["id"] == reclamo["id"]
        assert body["estado"] == CERRADO
        assert body["mensaje"] == MSG_CERRADO_EXITOSO

        detalle = await order["client"].get(
            f"{RECLAMOS}/{reclamo['id']}", headers=order["headers"]
        )
        assert detalle.status_code == 200, detalle.text
        assert detalle.json()["estado"] == CERRADO

        reposicion = await order["client"].get(
            f"{PEDIDOS}/{reclamo['pedido_reposicion_numero']}", headers=order["headers"]
        )
        assert reposicion.status_code == 200, reposicion.text
        assert reposicion.json()["estado"] == ENTREGADO, (
            "Al dar conformidad, el pedido de reposicion pasa a 'Entregado'"
        )

    @pytest.mark.parametrize(
        "check",
        [
            "comprobante_verificado",
            "pertenencia_botica_verificada",
            "defecto_fisico_verificado",
        ],
    )
    async def test_conforme_con_check_en_false_retorna_422(self, make_client, check):
        order, reclamo = await reclamo_aprobado(make_client)
        response = await inspeccionar(
            order, reclamo["id"], body=inspeccion_body(**{check: False})
        )
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_CONFORMIDAD_INCOMPLETA

        detalle = await order["client"].get(
            f"{RECLAMOS}/{reclamo['id']}", headers=order["headers"]
        )
        assert detalle.json()["estado"] == APROBADO, (
            "Una conformidad incompleta no debe cambiar el estado del reclamo"
        )

    async def test_falla_sin_motivo_retorna_422(self, make_client):
        order, reclamo = await reclamo_aprobado(make_client)
        body = inspeccion_body("falla")
        body.pop("motivo_falla")
        response = await inspeccionar(order, reclamo["id"], body=body)
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_FALLA_SIN_MOTIVO

        detalle = await order["client"].get(
            f"{RECLAMOS}/{reclamo['id']}", headers=order["headers"]
        )
        assert detalle.json()["estado"] == APROBADO, (
            "Una falla sin motivo no debe registrar intento"
        )

    async def test_fallas_secuenciales_escalan_al_tercer_intento(self, make_client):
        order = await delivered_order(make_client)
        antes = stock_row(order["producto_id"])
        registro = await registrar_reclamo(order)
        assert registro.status_code == 201, registro.text
        reclamo = registro.json()

        for intento in (1, 2):
            response = await inspeccionar(order, reclamo["id"], body=inspeccion_body("falla"))
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["estado"] == REINTENTO
            assert body["intentos_adicionales_realizados"] == intento
            assert body["intentos_restantes"] == 3 - intento
            assert body["mensaje"] == MSG_REINTENTO

        tercero = await inspeccionar(order, reclamo["id"], body=inspeccion_body("falla"))
        assert tercero.status_code == 200, tercero.text
        body = tercero.json()
        assert body["estado"] == ESCALADO
        assert body["intentos_adicionales_realizados"] == 3
        assert body["intentos_restantes"] == 0
        assert body["mensaje"] == MSG_ESCALADO

        detalle = await order["client"].get(
            f"{RECLAMOS}/{reclamo['id']}", headers=order["headers"]
        )
        assert detalle.json()["estado"] == ESCALADO

        despues = stock_row(order["producto_id"])
        assert despues is not None
        assert despues[0] == antes[0] and despues[1] == antes[1], (
            "Al escalar a supervision el producto nuevo debe volver al stock "
            f"disponible. antes={antes} despues={despues}"
        )

        bloqueado = await inspeccionar(
            order, reclamo["id"], body=inspeccion_body("falla")
        )
        assert bloqueado.status_code == 409, bloqueado.text
        assert bloqueado.json()["detail"] == MSG_ESTADO_FINAL

    async def test_reintento_sobre_reclamo_cerrado_retorna_409(self, make_client):
        order, reclamo = await reclamo_aprobado(make_client)
        conforme = await inspeccionar(order, reclamo["id"])
        assert conforme.status_code == 200, conforme.text
        response = await inspeccionar(order, reclamo["id"], body=inspeccion_body("falla"))
        assert response.status_code == 409, response.text
        assert response.json()["detail"] == MSG_ESTADO_FINAL


# ---------------------------------------------------------------------------
# Politica de cero reembolsos (contrato §5).
# ---------------------------------------------------------------------------
class TestCeroReembolsos:
    async def test_solicitud_de_reembolso_esta_bloqueada(self, make_client):
        _, reclamo = await reclamo_aprobado(make_client)
        actor = await admin_session(make_client)
        response = await actor["client"].post(
            f"{RECLAMOS}/{reclamo['id']}/reembolso", headers=actor["headers"]
        )
        assert response.status_code == 405, response.text
        assert response.json()["detail"] == MSG_CERO_REEMBOLSOS

    async def test_payload_que_fuerza_accion_reembolso_retorna_400_o_422(self, make_client):
        _, reclamo = await reclamo_aprobado(make_client)
        actor = await admin_session(make_client)
        response = await actor["client"].post(
            f"{RECLAMOS}/{reclamo['id']}/reembolso",
            json={"accion": "reembolso"},
            headers=actor["headers"],
        )
        assert response.status_code in (400, 422), response.text
        assert response.json()["detail"] == MSG_ACCION_NO_PERMITIDA


# ---------------------------------------------------------------------------
# Consulta y filtrado de reclamos (contrato §6).
# ---------------------------------------------------------------------------
class TestConsulta:
    async def test_cliente_solo_ve_sus_propios_reclamos(self, make_client):
        order_a, reclamo_a = await reclamo_aprobado(make_client)
        order_b, reclamo_b = await reclamo_aprobado(make_client)

        listado_a = await order_a["client"].get(
            RECLAMOS, headers=order_a["headers"]
        )
        assert listado_a.status_code == 200, listado_a.text
        items_a = assert_estructura_listado(listado_a.json())
        ids_a = {item.get("id") for item in items_a}
        assert reclamo_a["id"] in ids_a
        assert reclamo_b["id"] not in ids_a, (
            "El cliente no debe ver reclamos de otro usuario"
        )

        listado_b = await order_b["client"].get(
            RECLAMOS, headers=order_b["headers"]
        )
        assert listado_b.status_code == 200, listado_b.text
        ids_b = {item.get("id") for item in assert_estructura_listado(listado_b.json())}
        assert reclamo_b["id"] in ids_b
        assert reclamo_a["id"] not in ids_b

        sin_reclamos = make_client()
        headers = await create_authenticated_headers(sin_reclamos)
        vacio = await sin_reclamos.get(RECLAMOS, headers=headers)
        assert vacio.status_code == 200, vacio.text
        assert assert_estructura_listado(vacio.json()) == [], (
            "Un cliente sin reclamos no debe ver reclamos de otros usuarios"
        )

    async def test_admin_lista_todos_y_filtra_por_estado_y_pedido(self, make_client):
        order_a, reclamo_a = await reclamo_aprobado(make_client)
        order_b, reclamo_b = await reclamo_aprobado(make_client)
        falla = await inspeccionar(order_b, reclamo_b["id"], body=inspeccion_body("falla"))
        assert falla.status_code == 200, falla.text

        admin = await admin_session(make_client)
        todos = await admin["client"].get(RECLAMOS, headers=admin["headers"])
        assert todos.status_code == 200, todos.text
        ids = {item.get("id") for item in assert_estructura_listado(todos.json())}
        assert {reclamo_a["id"], reclamo_b["id"]} <= ids

        aprobados = await admin["client"].get(
            RECLAMOS, params={"estado": APROBADO}, headers=admin["headers"]
        )
        assert aprobados.status_code == 200, aprobados.text
        items_aprobados = assert_estructura_listado(aprobados.json())
        assert all(item.get("estado") == APROBADO for item in items_aprobados)
        ids_aprobados = {item.get("id") for item in items_aprobados}
        assert reclamo_a["id"] in ids_aprobados
        assert reclamo_b["id"] not in ids_aprobados

        por_pedido = await admin["client"].get(
            RECLAMOS,
            params={"pedido_numero": order_a["numero"]},
            headers=admin["headers"],
        )
        assert por_pedido.status_code == 200, por_pedido.text
        items_pedido = assert_estructura_listado(por_pedido.json())
        assert items_pedido, "El filtro por pedido_numero debe devolver el reclamo"
        assert all(
            item.get("pedido_origen_numero") == order_a["numero"]
            for item in items_pedido
        )
        assert reclamo_b["id"] not in {item.get("id") for item in items_pedido}

    async def test_reclamo_ajeno_retorna_404(self, make_client):
        _, reclamo = await reclamo_aprobado(make_client)
        intruso = make_client()
        headers = await create_authenticated_headers(intruso)
        response = await intruso.get(f"{RECLAMOS}/{reclamo['id']}", headers=headers)
        assert_domain_404(response)


# ---------------------------------------------------------------------------
# Asignacion de motorizado heredada del pedido de reposicion (contrato v2).
# ---------------------------------------------------------------------------
class TestAsignacionMotorizado:
    async def test_motorizado_ve_el_reclamo_al_asignarse_su_pedido_de_reposicion(
        self, make_client
    ):
        order, reclamo = await reclamo_aprobado(make_client)
        motorizado = order["motorizado"]
        admin = order["admin"]

        antes = await motorizado["client"].get(
            RECLAMOS, headers=motorizado["headers"]
        )
        assert antes.status_code == 200, antes.text
        ids_antes = {
            item.get("id") for item in assert_estructura_listado(antes.json())
        }
        assert reclamo["id"] not in ids_antes, (
            "Sin asignacion del pedido de reposicion el motorizado no debe ver el reclamo"
        )

        asignado = await admin["client"].post(
            ASIGNACIONES,
            json={
                "zona_id": order["zona_id"],
                "pedido_numeros": [reclamo["pedido_reposicion_numero"]],
                "motorizado_id": motorizado["usuario"]["id"],
            },
            headers=admin["headers"],
        )
        assert asignado.status_code == 200, asignado.text

        despues = await motorizado["client"].get(
            RECLAMOS, headers=motorizado["headers"]
        )
        assert despues.status_code == 200, despues.text
        ids_despues = {
            item.get("id") for item in assert_estructura_listado(despues.json())
        }
        assert reclamo["id"] in ids_despues, (
            "Al asignarse el pedido de reposicion, el reclamo debe quedar disponible "
            "para el motorizado"
        )


# ---------------------------------------------------------------------------
# Lo que el contrato exige pero no define una interfaz observable.
# ---------------------------------------------------------------------------
class TestNoVerificado:
    @pytest.mark.skip(
        reason="NO VERIFICADO: el contrato exige asentar el producto recogido como "
        "'merma_averiada', pero no define un endpoint ni campo observable para "
        "comprobarlo. Reportado al LEAD."
    )
    async def test_merma_averiada_asentada(self, make_client):
        ...

    @pytest.mark.skip(
        reason="NO VERIFICADO: 'se bloquean nuevos despachos' tras escalar no define "
        "codigo ni mensaje observable; el efecto de stock si se verifica en "
        "test_fallas_secuenciales_escalan_al_tercer_intento. Reportado al LEAD."
    )
    async def test_despachos_bloqueados_tras_escalar(self, make_client):
        ...
