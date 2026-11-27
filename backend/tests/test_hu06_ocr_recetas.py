"""Pruebas de caja negra para HU-06 (OCR de recetas y bloqueo W-03).

Escritas desde `contratos/CONTRATO-HU-06.md` v1 y `CONTRATO-HU-07.md` v2, sin
inspeccionar la implementacion. Se usan los marcadores acordados en el NOMBRE
del archivo para el proveedor OCR determinista de APP_ENV=test. Las aserciones
son estructurales: se usan los nombres/productos devueltos por la API.
"""

import asyncio
import json
import os
import uuid

import pytest
import pytest_asyncio
import pymysql

OCR_UPLOAD = "/api/v1/ocr/recetas"
OCR_JOBS = "/api/v1/ocr/jobs"
CHECKOUT = "/api/v1/checkout"
CART = "/api/v1/carrito"
CART_ITEMS = "/api/v1/carrito/items"
CATALOG = "/api/v1/catalogo/buscar"
REGISTRO = "/api/v1/auth/registro"
ACTIVAR = "/api/v1/auth/activar"
LOGIN = "/api/v1/auth/login"
QUEUE = "email.auth"

PASSWORD = "Password123!"
FORMAT_MESSAGE = "Formato de archivo no soportado. Usa JPG, PNG o PDF"
SIZE_MESSAGE = "El archivo supera el tamaño máximo permitido"
RECETA_BLOCK_MESSAGE = "Debes adjuntar y validar tu receta médica para continuar con el pago"
LOW_CONFIDENCE_MESSAGE = (
    "No pudimos leer la receta con suficiente confianza. Revisa y confirma los medicamentos"
)
MAX_SIZE_BYTES = 10 * 1024 * 1024
POLL_TIMEOUT_SECONDS = 15


@pytest_asyncio.fixture
async def api_client(app):
    import httpx
    from httpx import ASGITransport

    host = f"hu06-{uuid.uuid4().hex}"
    transport = ASGITransport(app=app, client=(host, 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture(autouse=True)
def ocr_test_provider(default_env, monkeypatch):
    """Activa el proveedor OCR determinista acordado para pruebas."""
    monkeypatch.setenv("APP_ENV", "test")
    yield


@pytest.fixture(autouse=True)
def reset_shared_inventory(default_env):
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


def assert_domain_404(response) -> None:
    assert response.status_code == 404, response.text
    assert response.json().get("detail") != "Not Found", f"Endpoint no implementado: {response.text}"


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
    email = f"hu06.{uuid.uuid4().hex[:12]}@ejemplo.com"
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


async def cart_items(client, headers: dict) -> list[dict]:
    response = await client.get(CART, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    return body["items_oferta"] + body["items_regulares"]


async def upload_receta(client, headers: dict, marker: str, *, content: bytes = b"contenido"):
    extension = "jpg"
    media_type = "image/jpeg"
    return await client.post(
        OCR_UPLOAD,
        files={"archivo": (f"{marker}.{extension}", content, media_type)},
        headers=headers,
    )


async def wait_for_job(client, headers: dict, job_id: str) -> dict:
    """Sondea el job hasta estado terminal (sin asumir timing interno)."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + POLL_TIMEOUT_SECONDS
    last: dict | None = None
    while loop.time() < deadline:
        response = await client.get(f"{OCR_JOBS}/{job_id}", headers=headers)
        assert response.status_code == 200, response.text
        last = response.json()
        if last.get("estado") in {
            "completado",
            "requiere_validacion",
            "sin_stock",
            "error",
        }:
            return last
        await asyncio.sleep(0.1)
    pytest.fail(f"El job {job_id} no alcanzó estado terminal: {last}")


class TestAutenticacion:
    async def test_subir_receta_sin_sesion_retorna_401(self, api_client):
        response = await upload_receta(api_client, {}, "receta_ok")
        assert response.status_code == 401, response.text

    async def test_consultar_job_sin_sesion_retorna_401(self, api_client):
        response = await api_client.get(f"{OCR_JOBS}/job_inexistente")
        assert response.status_code == 401, response.text

    async def test_job_inexistente_retorna_404(self, api_client):
        headers = await create_authenticated_headers(api_client)
        response = await api_client.get(f"{OCR_JOBS}/job-{uuid.uuid4().hex}", headers=headers)
        assert_domain_404(response)

    async def test_job_ajeno_retorna_404(self, api_client):
        owner = await create_authenticated_headers(api_client)
        uploaded = await upload_receta(api_client, owner, "receta_ok")
        assert uploaded.status_code == 202, uploaded.text
        job_id = uploaded.json()["job_id"]

        other = await create_authenticated_headers(api_client)
        response = await api_client.get(f"{OCR_JOBS}/{job_id}", headers=other)
        assert_domain_404(response)


class TestSubida:
    async def test_subida_valida_retorna_202_con_polling(self, api_client):
        headers = await create_authenticated_headers(api_client)
        response = await upload_receta(api_client, headers, "receta_ok")
        assert response.status_code == 202, response.text
        body = response.json()
        assert body["job_id"]
        assert body["estado"] == "procesando"
        assert body["poll_interval_ms"] == 1500

    async def test_formato_invalido_retorna_422(self, api_client):
        headers = await create_authenticated_headers(api_client)
        response = await api_client.post(
            OCR_UPLOAD,
            files={"archivo": ("receta_ok.exe", b"x", "application/octet-stream")},
            headers=headers,
        )
        assert response.status_code == 422, response.text
        assert FORMAT_MESSAGE in response.json()["detail"]

    async def test_tamano_excedido_retorna_413(self, api_client):
        headers = await create_authenticated_headers(api_client)
        response = await upload_receta(
            api_client, headers, "receta_ok", content=b"x" * (MAX_SIZE_BYTES + 1)
        )
        assert response.status_code == 413, response.text
        assert SIZE_MESSAGE in response.json()["detail"]


class TestPolling:
    async def test_completado_inserta_items_y_asocia_receta(self, api_client):
        headers = await create_authenticated_headers(api_client)
        uploaded = await upload_receta(api_client, headers, "receta_ok")
        assert uploaded.status_code == 202, uploaded.text
        result = await wait_for_job(api_client, headers, uploaded.json()["job_id"])

        assert result["estado"] == "completado", result
        assert result["receta_id"] is not None
        assert result["items"]
        for item in result["items"]:
            assert {"producto_id", "nombre", "cantidad"} <= set(item)

        items = await cart_items(api_client, headers)
        for suggested in result["items"]:
            assert any(
                item["producto_id"] == suggested["producto_id"]
                and item["cantidad"] == suggested["cantidad"]
                for item in items
            ), f"Falta en el carrito: {suggested}"

    async def test_requiere_validacion_expone_sugeridos_sin_insertar(self, api_client):
        headers = await create_authenticated_headers(api_client)
        uploaded = await upload_receta(api_client, headers, "receta_lowconf")
        assert uploaded.status_code == 202, uploaded.text
        result = await wait_for_job(api_client, headers, uploaded.json()["job_id"])

        assert result["estado"] == "requiere_validacion", result
        assert result["items_sugeridos"]
        assert result["confianza"] is not None
        for suggested in result["items_sugeridos"]:
            assert {"texto", "cantidad", "confianza"} <= set(suggested)
        assert await cart_items(api_client, headers) == [], "No debe insertar antes de confirmar"

    async def test_sin_stock_no_inserta_parcial_y_mensaje_exacto(self, api_client):
        headers = await create_authenticated_headers(api_client)
        uploaded = await upload_receta(api_client, headers, "receta_nostock")
        assert uploaded.status_code == 202, uploaded.text
        result = await wait_for_job(api_client, headers, uploaded.json()["job_id"])

        assert result["estado"] == "sin_stock", result
        assert result["faltantes"]
        for missing in result["faltantes"]:
            assert {"nombre", "solicitado", "disponible"} <= set(missing)
        first_name = result["faltantes"][0]["nombre"]
        expected = (
            f"Lo sentimos, no contamos con stock disponible de {first_name} "
            "para completar su receta médica"
        )
        assert result["mensaje"] == expected
        assert await cart_items(api_client, headers) == [], "PA-03: sin inserción parcial"

    @pytest.mark.skip(
        reason="NO VERIFICADO: el seam acordado define marcadores solo para exito, baja confianza y quiebre de stock; no hay marcador determinista para error tecnico del motor."
    )
    async def test_estado_error(self, api_client):
        ...


class TestConfirmar:
    async def test_confirmar_valido_completa_e_inserta(self, api_client):
        headers = await create_authenticated_headers(api_client)
        uploaded = await upload_receta(api_client, headers, "receta_lowconf")
        assert uploaded.status_code == 202, uploaded.text
        job_id = uploaded.json()["job_id"]
        result = await wait_for_job(api_client, headers, job_id)
        assert result["estado"] == "requiere_validacion", result

        resolved = [
            {"producto_id": item["producto_id"], "cantidad": item["cantidad"]}
            for item in result["items_sugeridos"]
            if item.get("producto_id") is not None
        ]
        assert resolved, "El fallback debe exponer al menos un producto resoluble"
        response = await api_client.post(
            f"{OCR_JOBS}/{job_id}/confirmar", json={"items": resolved}, headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["estado"] == "completado"
        assert body["receta_id"] is not None
        inserted = await cart_items(api_client, headers)
        for item in resolved:
            assert any(cart["producto_id"] == item["producto_id"] for cart in inserted)

    async def test_confirmar_job_sin_stock_retorna_409(self, api_client):
        headers = await create_authenticated_headers(api_client)
        uploaded = await upload_receta(api_client, headers, "receta_nostock")
        assert uploaded.status_code == 202, uploaded.text
        job_id = uploaded.json()["job_id"]
        result = await wait_for_job(api_client, headers, job_id)
        assert result["estado"] == "sin_stock", result

        response = await api_client.post(
            f"{OCR_JOBS}/{job_id}/confirmar",
            json={"items": [{"producto_id": 1, "cantidad": 1}]},
            headers=headers,
        )
        assert response.status_code == 409, response.text
        assert await cart_items(api_client, headers) == [], "PA-03: sin inserción parcial"

    async def test_confirmar_job_ya_completado_retorna_409(self, api_client):
        headers = await create_authenticated_headers(api_client)
        uploaded = await upload_receta(api_client, headers, "receta_ok")
        assert uploaded.status_code == 202, uploaded.text
        job_id = uploaded.json()["job_id"]
        assert (await wait_for_job(api_client, headers, job_id))["estado"] == "completado"

        response = await api_client.post(
            f"{OCR_JOBS}/{job_id}/confirmar",
            json={"items": [{"producto_id": 1, "cantidad": 1}]},
            headers=headers,
        )
        assert response.status_code == 409, response.text

    async def test_confirmar_job_ajeno_retorna_404(self, api_client):
        owner = await create_authenticated_headers(api_client)
        uploaded = await upload_receta(api_client, owner, "receta_lowconf")
        assert uploaded.status_code == 202, uploaded.text
        job_id = uploaded.json()["job_id"]
        other = await create_authenticated_headers(api_client)
        response = await api_client.post(
            f"{OCR_JOBS}/{job_id}/confirmar",
            json={"items": [{"producto_id": 1, "cantidad": 1}]},
            headers=other,
        )
        assert_domain_404(response)


class TestCheckoutReceta:
    async def test_checkout_bloquea_producto_requiere_receta(self, api_client):
        headers = await create_authenticated_headers(api_client)
        products = await get_catalog_products(api_client)
        recipe_product = next((p for p in products if p["requiere_receta"]), None)
        assert recipe_product is not None, "El seed debe exponer un producto con requiere_receta"
        added = await api_client.post(
            CART_ITEMS,
            json={"producto_id": recipe_product["id"], "cantidad": 1},
            headers=headers,
        )
        assert added.status_code == 200, added.text

        response = await api_client.post(
            CHECKOUT, json={"metodo_entrega": "retiro"}, headers=headers
        )
        assert response.status_code == 409, response.text
        assert RECETA_BLOCK_MESSAGE in response.json()["detail"]

    async def test_checkout_con_receta_validada_continua_hu07(self, api_client):
        headers = await create_authenticated_headers(api_client)
        products = await get_catalog_products(api_client)
        recipe_product = next((p for p in products if p["requiere_receta"]), None)
        assert recipe_product is not None, "El seed debe exponer un producto con requiere_receta"
        added = await api_client.post(
            CART_ITEMS,
            json={"producto_id": recipe_product["id"], "cantidad": 1},
            headers=headers,
        )
        assert added.status_code == 200, added.text

        uploaded = await upload_receta(api_client, headers, "receta_ok")
        assert uploaded.status_code == 202, uploaded.text
        result = await wait_for_job(api_client, headers, uploaded.json()["job_id"])
        assert result["estado"] == "completado", result

        response = await api_client.post(
            CHECKOUT, json={"metodo_entrega": "retiro"}, headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["payment_intent_id"]
        assert body["moneda"] == "PEN"


class TestPrivacidad:
    @pytest.mark.skip(
        reason="NO VERIFICADO: el borrado del documento original (LPDP) no es observable desde la API pública; solo se conserva el resultado estructurado."
    )
    async def test_documento_original_eliminado(self, api_client):
        ...
