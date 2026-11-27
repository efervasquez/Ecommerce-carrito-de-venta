"""Pruebas de caja negra para HU-02 (recuperacion de contrasena).

Fuente unica: contratos/CONTRATO-HU-02.md v1, aprobada 2026-11-23.
Las pruebas usan solamente HTTP y el evento observable de RabbitMQ.
"""

import asyncio
import json
import os
import time
import uuid

import pytest
import pytest_asyncio

RECUPERAR = "/api/v1/auth/recuperar"
RESTABLECER = "/api/v1/auth/restablecer"
REGISTRO = "/api/v1/auth/registro"
ACTIVAR = "/api/v1/auth/activar"

COLA_EMAIL_AUTH = "email.auth"
EVENTO_RECUPERACION = "auth.recuperacion_solicitada"
MSG_RECUPERAR = "Si el email existe, recibirás un correo"
MSG_EMAIL_INVALIDO = "Formato de correo electrónico inválido"
MSG_RATE_LIMIT = "Demasiadas solicitudes. Por favor, intente nuevamente en unos minutos."
MSG_PASSWORD_DEBIL = "La contraseña debe tener al menos 8 caracteres e incluir mayúsculas, minúsculas y números."
PASSWORD_OK = "Password123!"


def unique_email() -> str:
    return f"recuperacion.{uuid.uuid4().hex[:12]}@ejemplo.com"


@pytest_asyncio.fixture
async def hu02_client(app):
    import httpx
    from httpx import ASGITransport

    host = f"hu02-{uuid.uuid4().hex}"
    transport = ASGITransport(app=app, client=(host, 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def hu02_second_client(app):
    import httpx
    from httpx import ASGITransport

    host = f"hu02-second-{uuid.uuid4().hex}"
    transport = ASGITransport(app=app, client=(host, 50001))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def hu02_third_client(app):
    import httpx
    from httpx import ASGITransport

    host = f"hu02-third-{uuid.uuid4().hex}"
    transport = ASGITransport(app=app, client=(host, 50002))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


async def _rabbit_queue():
    import aio_pika

    url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()
    queue = await channel.declare_queue(COLA_EMAIL_AUTH, durable=True)
    return connection, queue


async def consume_email_event(timeout: float = 10.0) -> dict:
    connection, queue = await _rabbit_queue()
    try:
        async with queue.iterator(timeout=1) as iterator:
            message = await asyncio.wait_for(iterator.__anext__(), timeout=timeout)
            async with message.process():
                return json.loads(message.body)
    finally:
        await connection.close()


async def purge_email_queue() -> None:
    connection, queue = await _rabbit_queue()
    try:
        await queue.purge()
    finally:
        await connection.close()


async def create_active_account(client) -> str:
    email = unique_email()
    registration = await client.post(REGISTRO, json={"email": email})
    assert registration.status_code == 200, registration.text
    activation_event = await consume_email_event()
    activation = await client.post(
        ACTIVAR,
        json={"token": activation_event["payload"]["token"], "password": PASSWORD_OK},
    )
    assert activation.status_code == 200, activation.text
    return email


async def request_recovery(client, email: str):
    return await client.post(RECUPERAR, json={"email": email})


async def request_recovery_and_get_event(client, email: str) -> tuple[object, dict]:
    response = await request_recovery(client, email)
    assert response.status_code == 200, response.text
    return response, await consume_email_event()


class TestSolicitarRecuperacion:
    async def test_email_existente_retorna_200_mensaje_y_publica_evento(
        self, hu02_client, hu02_second_client
    ):
        await purge_email_queue()
        email = await create_active_account(hu02_client)
        response, event = await request_recovery_and_get_event(hu02_second_client, email)

        assert response.json() == {"message": MSG_RECUPERAR}
        assert event["evento"] == EVENTO_RECUPERACION
        assert event["payload"]["email"] == email

    async def test_email_inexistente_retorna_mismo_json_y_timing_similar(
        self, hu02_client, hu02_second_client
    ):
        email = await create_active_account(hu02_client)
        existing_start = time.monotonic()
        existing = await request_recovery(hu02_second_client, email)
        existing_elapsed = time.monotonic() - existing_start
        await consume_email_event()

        unknown_start = time.monotonic()
        unknown = await request_recovery(hu02_second_client, unique_email())
        unknown_elapsed = time.monotonic() - unknown_start

        assert existing.status_code == 200
        assert unknown.status_code == 200
        assert existing.json() == {"message": MSG_RECUPERAR}
        assert unknown.json() == existing.json()
        assert abs(existing_elapsed - unknown_elapsed) < 2.0

    async def test_cooldown_no_publica_evento_adicional(
        self, hu02_client, hu02_second_client
    ):
        await purge_email_queue()
        email = await create_active_account(hu02_client)
        first = await request_recovery(hu02_second_client, email)
        assert first.status_code == 200
        event = await consume_email_event()
        assert event["payload"]["email"] == email

        second = await request_recovery(hu02_second_client, email)
        assert second.status_code == 200
        assert second.json() == {"message": MSG_RECUPERAR}
        with pytest.raises(asyncio.TimeoutError):
            await consume_email_event(timeout=2.0)

    @pytest.mark.skip(
        reason="NO VERIFICADO: el cooldown de 15 minutos impide provocar el limite diario desde la interfaz observable sin avanzar el reloj."
    )
    async def test_limite_diario_tres_solicitudes_no_publica_una_cuarta(self):
        ...

    async def test_email_invalido_retorna_422(self, hu02_client):
        response = await request_recovery(hu02_client, "correo_sin_dominio.com")
        assert response.status_code == 422
        assert response.json() == {"detail": MSG_EMAIL_INVALIDO}

    async def test_payload_vacio_retorna_422(self, hu02_client):
        response = await hu02_client.post(RECUPERAR, json={})
        assert response.status_code == 422

    async def test_campo_email_ausente_retorna_422(self, hu02_client):
        response = await hu02_client.post(RECUPERAR, json={"correo": "cliente@ejemplo.com"})
        assert response.status_code == 422

    async def test_rate_limit_por_ip_retorna_429(self, hu02_client):
        for _ in range(3):
            response = await request_recovery(hu02_client, "correo_invalido")
            assert response.status_code == 422
        response = await request_recovery(hu02_client, "correo_invalido")
        assert response.status_code == 429
        assert response.json() == {"detail": MSG_RATE_LIMIT}


class TestEventoRecuperacion:
    async def test_evento_durable_tiene_nombre_y_payload_exactos(
        self, hu02_client, hu02_second_client
    ):
        await purge_email_queue()
        email = await create_active_account(hu02_client)
        _, event = await request_recovery_and_get_event(hu02_second_client, email)

        assert event["evento"] == EVENTO_RECUPERACION
        uuid.UUID(event["correlation_id"])
        assert event["timestamp"]
        payload = event["payload"]
        assert payload["email"] == email
        token = uuid.UUID(payload["token"])
        assert str(token) == payload["token"]
        assert f"/restablecer?token={payload['token']}" in payload["url_recuperacion"]
        assert payload["expira_en"]


class TestRestablecer:
    async def test_token_valido_password_fuerte_retorna_200(
        self, hu02_client, hu02_second_client
    ):
        email = await create_active_account(hu02_client)
        _, event = await request_recovery_and_get_event(hu02_second_client, email)
        response = await hu02_second_client.post(
            RESTABLECER,
            json={"token": event["payload"]["token"], "password": "NuevaClave2026!"},
        )
        assert response.status_code == 200, response.text
        assert isinstance(response.json().get("message"), str)
        assert response.json()["message"]

    async def test_token_reutilizado_retorna_400_con_mensaje_generico(
        self, hu02_client, hu02_second_client, hu02_third_client
    ):
        email = await create_active_account(hu02_client)
        _, event = await request_recovery_and_get_event(hu02_second_client, email)
        token = event["payload"]["token"]
        first = await hu02_second_client.post(
            RESTABLECER, json={"token": token, "password": "NuevaClave2026!"}
        )
        assert first.status_code == 200
        reused = await hu02_second_client.post(
            RESTABLECER, json={"token": token, "password": "OtraClave2026!"}
        )
        nonexistent = await hu02_third_client.post(
            RESTABLECER, json={"token": str(uuid.uuid4()), "password": PASSWORD_OK}
        )
        assert reused.status_code == 400
        assert nonexistent.status_code == 400
        assert isinstance(reused.json().get("detail"), str)
        assert reused.json()["detail"] == nonexistent.json()["detail"]

    @pytest.mark.skip(
        reason="NO VERIFICADO: no existe una interfaz observable para crear un token recuperacion expirado sin esperar una hora o manipular el reloj/DB."
    )
    async def test_token_expirado_retorna_400_mismo_mensaje(self):
        ...

    async def test_token_inexistente_o_alterado_retorna_400_mismo_mensaje(self, hu02_client):
        unknown = await hu02_client.post(
            RESTABLECER, json={"token": str(uuid.uuid4()), "password": PASSWORD_OK}
        )
        altered = await hu02_client.post(
            RESTABLECER, json={"token": "token-alterado", "password": PASSWORD_OK}
        )
        assert unknown.status_code == 400
        assert altered.status_code == 400
        assert unknown.json()["detail"] == altered.json()["detail"]

    async def test_password_debil_retorna_422_y_token_permanece_sin_usar(
        self, hu02_client, hu02_second_client
    ):
        email = await create_active_account(hu02_client)
        _, event = await request_recovery_and_get_event(hu02_second_client, email)
        token = event["payload"]["token"]
        weak = await hu02_second_client.post(
            RESTABLECER, json={"token": token, "password": "password"}
        )
        assert weak.status_code == 422
        assert weak.json() == {"detail": MSG_PASSWORD_DEBIL}
        strong = await hu02_second_client.post(
            RESTABLECER, json={"token": token, "password": "NuevaClave2026!"}
        )
        assert strong.status_code == 200

    async def test_payload_vacio_retorna_422(self, hu02_client):
        response = await hu02_client.post(RESTABLECER, json={})
        assert response.status_code == 422

    async def test_payload_sin_token_o_password_retorna_422(self, hu02_client):
        missing_token = await hu02_client.post(RESTABLECER, json={"password": PASSWORD_OK})
        missing_password = await hu02_client.post(
            RESTABLECER, json={"token": str(uuid.uuid4())}
        )
        assert missing_token.status_code == 422
        assert missing_password.status_code == 422
