"""Pruebas de caja negra para HU-10 (contingencia de inventario y edicion de productos).

Escritas desde `contratos/CONTRATO-HU-10.md` v1 (aprobado), sin inspeccionar la
implementacion. Rutas, campos, roles, codigos y textos se toman de la seccion
"Nombres que no se negocian" y de las tablas de comportamiento del contrato.

Los productos de prueba usan el prefijo `HU10-` en `nombre` y `componentes` para
que el fixture pueda limpiarlos de la tabla local `productos` sin tocar el seed
del catalogo. Toda la interaccion es por API con token de administrador (seed
RBAC de `APP_ENV=test`).
"""

import asyncio
import json
import os
import uuid

import pytest
import pymysql

# ---------------------------------------------------------------------------
# Semilla de usuarios RBAC (admin / motorizado). Se fija antes de que
# `src.main` cargue la configuracion para que el seed del DEV cree los usuarios.
# `setdefault` respeta los valores ya fijados por otros modulos de la sesion.
# ---------------------------------------------------------------------------
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SEED_RBAC_USERS", "true")

ADMIN_EMAIL = os.environ.setdefault("SEED_ADMIN_EMAIL", "hu10.admin@ejemplo.com")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "Admin12345!")
MOTORIZADO_EMAIL = os.environ.setdefault("SEED_MOTORIZADO_EMAIL", "hu10.motorizado@ejemplo.com")
os.environ.setdefault("SEED_MOTORIZADO_PASSWORD", "Moto12345!")

ADMIN_PASSWORD = os.environ["SEED_ADMIN_PASSWORD"]
MOTORIZADO_PASSWORD = os.environ["SEED_MOTORIZADO_PASSWORD"]

PRODUCTOS = "/api/v1/backoffice/productos"
REGISTRO = "/api/v1/auth/registro"
ACTIVAR = "/api/v1/auth/activar"
LOGIN = "/api/v1/auth/login"
QUEUE = "email.auth"

PASSWORD = "Password123!"
PREFIJO = "HU10-"

MSG_STOCK = "La cantidad de existencias debe ser un número entero mayor o igual a cero."
MSG_PRECIO = "El precio regular debe ser mayor a cero."
MSG_DESCUENTO = "El porcentaje de descuento debe estar entre 0 y 100."
MSG_METODOS = "Los métodos de entrega permitidos son delivery y retiro."
MSG_PRODUCTO_NO_ENCONTRADO = "Producto no encontrado."
MSG_RBAC = "Acceso restringido a operadores de inventario y administradores."

CAMPOS_OBLIGATORIOS = ("nombre", "componentes", "precio_regular", "presentacion", "detalle")
CAMPOS_EDICION = (
    "nombre",
    "componentes",
    "precio_regular",
    "descuento_porcentaje",
    "precios_bajos",
    "requiere_receta",
    "presentacion",
    "metodos_entrega",
    "detalle",
    "contraindicaciones",
    "precauciones_advertencias",
    "reacciones_adversas",
    "imagen_url",
)
CAMPOS_LISTA = (
    "id",
    "nombre",
    "componentes",
    "precio_regular",
    "descuento_porcentaje",
    "stock_disponible",
    "stock_reservado",
    "precios_bajos",
    "requiere_receta",
)


# ---------------------------------------------------------------------------
# Clientes con IP propia (evita el rate limit de auth compartido por IP).
# ---------------------------------------------------------------------------
@pytest.fixture
def make_client(app):
    def _make():
        import httpx
        from httpx import ASGITransport

        host = f"hu10-{uuid.uuid4().hex}"
        transport = ASGITransport(app=app, client=(host, 50000))
        return httpx.AsyncClient(transport=transport, base_url="http://testserver")

    return _make


def _borrar_productos_hu10() -> None:
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
            tablas = {row[0] for row in cursor.fetchall()}
            if "productos" not in tablas:
                return
            cursor.execute("SELECT id FROM productos WHERE nombre LIKE %s", (f"{PREFIJO}%",))
            ids = [row[0] for row in cursor.fetchall()]
            if not ids:
                return
            placeholders = ", ".join(["%s"] * len(ids))
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            if "inventario_stock" in tablas:
                cursor.execute(
                    f"DELETE FROM inventario_stock WHERE producto_id IN ({placeholders})",
                    ids,
                )
            cursor.execute(
                f"DELETE FROM productos WHERE id IN ({placeholders})", ids
            )
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
    finally:
        connection.close()


@pytest.fixture(autouse=True)
def reset_hu10_products(default_env):
    """Cada prueba parte sin productos `HU10-*` de corridas anteriores."""
    _borrar_productos_hu10()
    yield
    _borrar_productos_hu10()


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
    email = f"hu10.{uuid.uuid4().hex[:12]}@ejemplo.com"
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
# Helpers de producto.
# ---------------------------------------------------------------------------
def producto_payload(**overrides) -> dict:
    token = uuid.uuid4().hex[:8]
    payload = {
        "nombre": f"{PREFIJO}Amoxicilina-{token}",
        "componentes": f"{PREFIJO}Amoxicilina trihidrato {token}",
        "precio_regular": 12.50,
        "moneda": "PEN",
        "stock_disponible": 100,
        "presentacion": "Caja con 20 cápsulas",
        "metodos_entrega": ["delivery", "retiro"],
        "requiere_receta": True,
        "detalle": "Antibiótico bactericida de amplio espectro.",
        "imagen_url": "https://ejemplo.com/amoxicilina.png",
        "descuento_porcentaje": 0.0,
        "precios_bajos": False,
        "contraindicaciones": "Hipersensibilidad a penicilinas.",
        "precauciones_advertencias": "Ajustar dosis en insuficiencia renal.",
        "reacciones_adversas": "Náuseas, diarrea, erupción cutánea.",
    }
    payload.update(overrides)
    return payload


def edicion_payload(**overrides) -> dict:
    """Cuerpo del PUT tal como lo define el contrato §4 (sin moneda ni stock)."""
    base = producto_payload()
    payload = {campo: base[campo] for campo in CAMPOS_EDICION}
    payload.update(overrides)
    return payload


async def crear_producto(admin: dict, **overrides) -> tuple[dict, dict]:
    payload = producto_payload(**overrides)
    response = await admin["client"].post(
        PRODUCTOS, json=payload, headers=admin["headers"]
    )
    assert response.status_code == 201, response.text
    return payload, response.json()


async def ajustar_stock(admin: dict, producto_id: int, stock_disponible, motivo: str = "Ajuste manual"):
    return await admin["client"].patch(
        f"{PRODUCTOS}/{producto_id}/stock",
        json={"stock_disponible": stock_disponible, "motivo": motivo},
        headers=admin["headers"],
    )


def assert_detalle_producto(item: dict) -> None:
    for campo in CAMPOS_LISTA:
        assert campo in item, f"Falta el campo '{campo}' en el producto: {item}"
    assert "stock_disponible" in item and "stock_reservado" in item


# ---------------------------------------------------------------------------
# RBAC y sesion (contrato §1).
# ---------------------------------------------------------------------------
class TestRBAC:
    ENDPOINTS = [
        ("GET", PRODUCTOS, {"json": None}),
        ("GET", f"{PRODUCTOS}/1", {"json": None}),
        ("POST", PRODUCTOS, {"json": producto_payload()}),
        ("PUT", f"{PRODUCTOS}/1", {"json": producto_payload()}),
        ("PATCH", f"{PRODUCTOS}/1/stock", {"json": {"stock_disponible": 1}}),
    ]

    @pytest.mark.parametrize("method,url,kwargs", ENDPOINTS)
    async def test_sin_sesion_retorna_401(self, make_client, method, url, kwargs):
        client = make_client()
        response = await client.request(method, url, **kwargs)
        assert response.status_code == 401, (
            f"{method} {url} sin JWT debe dar 401, obtuvo {response.status_code}: "
            f"{response.text}"
        )

    @pytest.mark.parametrize("method,url,kwargs", ENDPOINTS)
    async def test_motorizado_retorna_403(self, make_client, method, url, kwargs):
        actor = await motorizado_session(make_client)
        response = await actor["client"].request(
            method, url, **kwargs, headers=actor["headers"]
        )
        assert response.status_code == 403, response.text
        assert response.json()["detail"] == MSG_RBAC

    async def test_cliente_retorna_403(self, make_client):
        client = make_client()
        headers = await cliente_headers(client)
        response = await client.get(PRODUCTOS, headers=headers)
        assert response.status_code == 403, response.text
        assert response.json()["detail"] == MSG_RBAC

    async def test_admin_puede_listar(self, make_client):
        admin = await admin_session(make_client)
        response = await admin["client"].get(PRODUCTOS, headers=admin["headers"])
        assert response.status_code == 200, response.text
        body = response.json()
        assert isinstance(body.get("items"), list)
        assert "total" in body


# ---------------------------------------------------------------------------
# Alta manual de producto (contrato §2).
# ---------------------------------------------------------------------------
class TestAltaProducto:
    async def test_camino_feliz_crea_producto_e_inicializa_stock(self, make_client):
        admin = await admin_session(make_client)
        payload, body = await crear_producto(admin)

        assert body["id"]
        assert body["nombre"] == payload["nombre"]
        assert float(body["precio_regular"]) == 12.50
        assert float(body["stock_disponible"]) == 100

        detalle = await admin["client"].get(
            f"{PRODUCTOS}/{body['id']}", headers=admin["headers"]
        )
        assert detalle.status_code == 200, detalle.text
        detalle_body = detalle.json()
        assert_detalle_producto(detalle_body)
        assert float(detalle_body["stock_disponible"]) == 100
        assert float(detalle_body["stock_reservado"]) == 0
        assert detalle_body["precios_bajos"] is False
        assert detalle_body["requiere_receta"] is True

        listado = await admin["client"].get(
            PRODUCTOS, params={"q": payload["nombre"]}, headers=admin["headers"]
        )
        assert listado.status_code == 200, listado.text
        items = listado.json()["items"]
        assert any(item["id"] == body["id"] for item in items), (
            "El producto creado debe aparecer en el listado de inventario"
        )

    async def test_stock_inicial_negativo_retorna_422(self, make_client):
        admin = await admin_session(make_client)
        payload = producto_payload(stock_disponible=-5)
        response = await admin["client"].post(
            PRODUCTOS, json=payload, headers=admin["headers"]
        )
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_STOCK

        listado = await admin["client"].get(
            PRODUCTOS, params={"q": payload["nombre"]}, headers=admin["headers"]
        )
        assert listado.status_code == 200, listado.text
        assert listado.json()["items"] == [], "El alta invalida no debe persistir"

    @pytest.mark.parametrize("precio", [0, -3])
    async def test_precio_regular_no_positivo_retorna_422(self, make_client, precio):
        admin = await admin_session(make_client)
        payload = producto_payload(precio_regular=precio)
        response = await admin["client"].post(
            PRODUCTOS, json=payload, headers=admin["headers"]
        )
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_PRECIO

    @pytest.mark.parametrize("campo", CAMPOS_OBLIGATORIOS)
    async def test_falta_campo_obligatorio_retorna_422(self, make_client, campo):
        admin = await admin_session(make_client)
        payload = producto_payload()
        payload.pop(campo)
        response = await admin["client"].post(
            PRODUCTOS, json=payload, headers=admin["headers"]
        )
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == f"El campo {campo} es requerido."

    @pytest.mark.parametrize(
        "metodos",
        [["drone"], ["delivery", "drone"]],
    )
    async def test_metodos_de_entrega_invalidos_retornan_422(self, make_client, metodos):
        admin = await admin_session(make_client)
        payload = producto_payload(metodos_entrega=metodos)
        response = await admin["client"].post(
            PRODUCTOS, json=payload, headers=admin["headers"]
        )
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_METODOS


# ---------------------------------------------------------------------------
# Ajuste manual directo de stock (contrato §3).
# ---------------------------------------------------------------------------
class TestAjusteStock:
    async def test_camino_feliz_actualiza_disponible_y_devuelve_reservado(self, make_client):
        admin = await admin_session(make_client)
        _, producto = await crear_producto(admin)

        response = await ajustar_stock(admin, producto["id"], 50)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["id"] == producto["id"]
        assert body["producto_id"] == producto["id"]
        assert int(body["disponible"]) == 50
        assert int(body["reservado"]) == 0
        assert body["actualizado_en"]

        detalle = await admin["client"].get(
            f"{PRODUCTOS}/{producto['id']}", headers=admin["headers"]
        )
        assert detalle.status_code == 200, detalle.text
        assert float(detalle.json()["stock_disponible"]) == 50

    async def test_stock_negativo_retorna_422_sin_alterar(self, make_client):
        admin = await admin_session(make_client)
        _, producto = await crear_producto(admin)

        response = await ajustar_stock(admin, producto["id"], -10)
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_STOCK

        detalle = await admin["client"].get(
            f"{PRODUCTOS}/{producto['id']}", headers=admin["headers"]
        )
        assert float(detalle.json()["stock_disponible"]) == 100, (
            "Un ajuste invalido no debe alterar el stock"
        )

    @pytest.mark.parametrize("valor", [12.5, "abc"])
    async def test_stock_no_entero_retorna_422(self, make_client, valor):
        admin = await admin_session(make_client)
        _, producto = await crear_producto(admin)
        response = await ajustar_stock(admin, producto["id"], valor)
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_STOCK

    async def test_producto_inexistente_retorna_404(self, make_client):
        admin = await admin_session(make_client)
        response = await ajustar_stock(admin, 999999999, 10)
        assert response.status_code == 404, response.text
        assert response.json()["detail"] == MSG_PRODUCTO_NO_ENCONTRADO


# ---------------------------------------------------------------------------
# Edicion integral del producto (contrato §4).
# ---------------------------------------------------------------------------
class TestEdicionProducto:
    async def test_camino_feliz_actualiza_precio_oferta_y_precios_bajos(self, make_client):
        admin = await admin_session(make_client)
        payload, producto = await crear_producto(admin)
        nuevo = edicion_payload(
            nombre=f"{PREFIJO}Omeprazol-{uuid.uuid4().hex[:8]}",
            componentes=f"{PREFIJO}Omeprazol {uuid.uuid4().hex[:6]}",
            precio_regular=18.0,
            descuento_porcentaje=15.0,
            precios_bajos=True,
            requiere_receta=False,
            presentacion="Frasco con 30 cápsulas",
            detalle="Inhibidor de la bomba de protones.",
            contraindicaciones="Hipersensibilidad a omeprazol.",
            precauciones_advertencias="Consultar médico en embarazo.",
            reacciones_adversas="Cefalea, dolor abdominal.",
        )
        response = await admin["client"].put(
            f"{PRODUCTOS}/{producto['id']}", json=nuevo, headers=admin["headers"]
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["id"] == producto["id"]
        assert body["nombre"] == nuevo["nombre"]
        assert float(body["precio_regular"]) == 18.0
        assert float(body["descuento_porcentaje"]) == 15.0
        assert body["precios_bajos"] is True
        assert body["requiere_receta"] is False

        detalle = await admin["client"].get(
            f"{PRODUCTOS}/{producto['id']}", headers=admin["headers"]
        )
        assert detalle.status_code == 200, detalle.text
        detalle_body = detalle.json()
        assert detalle_body["nombre"] == nuevo["nombre"]
        assert float(detalle_body["precio_regular"]) == 18.0
        assert float(detalle_body["descuento_porcentaje"]) == 15.0
        assert detalle_body["precios_bajos"] is True
        assert detalle_body["presentacion"] == "Frasco con 30 cápsulas"
        assert detalle_body["contraindicaciones"] == "Hipersensibilidad a omeprazol."

        listado = await admin["client"].get(
            PRODUCTOS, params={"q": nuevo["nombre"]}, headers=admin["headers"]
        )
        assert listado.status_code == 200, listado.text
        assert any(item["id"] == producto["id"] for item in listado.json()["items"])

    @pytest.mark.parametrize("descuento", [150, -5])
    async def test_descuento_invalido_retorna_422(self, make_client, descuento):
        admin = await admin_session(make_client)
        _, producto = await crear_producto(admin)
        payload = edicion_payload(descuento_porcentaje=descuento)
        response = await admin["client"].put(
            f"{PRODUCTOS}/{producto['id']}", json=payload, headers=admin["headers"]
        )
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_DESCUENTO

    async def test_precio_regular_no_positivo_retorna_422(self, make_client):
        admin = await admin_session(make_client)
        _, producto = await crear_producto(admin)
        payload = edicion_payload(precio_regular=-2)
        response = await admin["client"].put(
            f"{PRODUCTOS}/{producto['id']}", json=payload, headers=admin["headers"]
        )
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == MSG_PRECIO

    async def test_producto_inexistente_retorna_404(self, make_client):
        admin = await admin_session(make_client)
        response = await admin["client"].put(
            f"{PRODUCTOS}/999999999",
            json=edicion_payload(),
            headers=admin["headers"],
        )
        assert response.status_code == 404, response.text
        assert response.json()["detail"] == MSG_PRODUCTO_NO_ENCONTRADO


# ---------------------------------------------------------------------------
# Consulta y listado en Backoffice (contrato §5).
# ---------------------------------------------------------------------------
class TestConsulta:
    async def test_listado_estructura_paginacion_y_total(self, make_client):
        admin = await admin_session(make_client)
        token = uuid.uuid4().hex[:8]
        for index in range(3):
            await crear_producto(
                admin,
                nombre=f"{PREFIJO}Lote-{token}-{index}",
                componentes=f"{PREFIJO}Componente-{token}",
            )

        primera = await admin["client"].get(
            PRODUCTOS,
            params={"q": token, "limit": 2, "offset": 0},
            headers=admin["headers"],
        )
        assert primera.status_code == 200, primera.text
        body = primera.json()
        assert body["total"] == 3, f"Total esperado 3 para el filtro: {body}"
        assert len(body["items"]) == 2
        for item in body["items"]:
            assert_detalle_producto(item)

        segunda = await admin["client"].get(
            PRODUCTOS,
            params={"q": token, "limit": 2, "offset": 2},
            headers=admin["headers"],
        )
        assert segunda.status_code == 200, segunda.text
        assert len(segunda.json()["items"]) == 1

    async def test_busqueda_por_componentes(self, make_client):
        admin = await admin_session(make_client)
        token = uuid.uuid4().hex[:10]
        _, producto = await crear_producto(
            admin,
            nombre=f"{PREFIJO}Busqueda-{uuid.uuid4().hex[:6]}",
            componentes=f"{PREFIJO}Ibuprofeno {token}",
        )
        response = await admin["client"].get(
            PRODUCTOS, params={"q": token}, headers=admin["headers"]
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert any(item["id"] == producto["id"] for item in body["items"]), (
            "La busqueda q debe coincidir con componentes"
        )

    async def test_detalle_completo_con_existencias(self, make_client):
        admin = await admin_session(make_client)
        payload, producto = await crear_producto(admin)
        response = await admin["client"].get(
            f"{PRODUCTOS}/{producto['id']}", headers=admin["headers"]
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert_detalle_producto(body)
        assert body["nombre"] == payload["nombre"]
        assert body["componentes"] == payload["componentes"]

    async def test_producto_inexistente_retorna_404(self, make_client):
        admin = await admin_session(make_client)
        response = await admin["client"].get(
            f"{PRODUCTOS}/999999999", headers=admin["headers"]
        )
        assert response.status_code == 404, response.text
        assert response.json()["detail"] == MSG_PRODUCTO_NO_ENCONTRADO
