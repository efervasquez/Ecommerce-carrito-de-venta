"""Pruebas de caja negra para HU-01 (Autoregistro y autenticacion de clientes).

Fuente de verdad: `contratos/CONTRATO-HU-01.md` (v1, aprobada 2026-10-16).

Todas las pruebas ejercitan la **interfaz observable** (API REST `/api/v1/auth/*` y,
donde el contrato lo exige, el bus de eventos RabbitMQ cola `email.auth`). No se
importa ninguna funcion, clase o servicio interno del DEV: solo se envia HTTP y se
lee el JSON de respuesta. Por eso, contra el codigo actual (sin implementar), estas
pruebas deben fallar (ROJO); deben pasar (VERDE) cuando el DEV implemente el contrato.

Los casos que NO se pueden provocar desde la interfaz observable (rate limiting
perimetral de IIS, token/JWT expirado, cuenta suspendida) quedan marcados con
`@pytest.mark.skip` y documentados como `NO VERIFICADO` en el informe.
"""

import asyncio
import json
import os
import time
import uuid

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Nombres que no se negocian (seccion 4 del contrato)
# ---------------------------------------------------------------------------
REGISTRO = "/api/v1/auth/registro"
ACTIVAR = "/api/v1/auth/activar"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"

COLA_EMAIL_AUTH = "email.auth"
EVENTO_ACTIVACION = "auth.activacion_solicitada"

MSG_REGISTRO = "Si el correo ingresado es válido, recibirás un enlace de activación en tu buzón."
MSG_ACTIVACION_OK = "Cuenta activada exitosamente. Ya puedes iniciar sesión."
MSG_ACTIVACION_INVALIDO = "El enlace de activación es inválido o ha expirado."
MSG_LOGIN_FALLO = "Credenciales inválidas o cuenta no activada."
MSG_SUSPENDIDA = "Cuenta suspendida. Por favor, contacte a soporte."
MSG_EMAIL_INVALIDO = "Formato de correo electrónico inválido"
MSG_PASSWORD_DEBIL = "La contraseña debe tener al menos 8 caracteres e incluir mayúsculas, minúsculas y números."
MSG_NO_AUTENTICADO = "No autenticado o token inválido."
MSG_TOKEN_EXPIRADO = "Token expirado. Inicie sesión nuevamente."
MSG_RATE_LIMIT = "Demasiadas solicitudes. Por favor, intente nuevamente en unos minutos."

PASSWORD_OK = "Password123!"
PASSWORD_DEBIL = "password"


def unique_email() -> str:
    return f"cliente.{uuid.uuid4().hex[:12]}@ejemplo.com"


@pytest_asyncio.fixture
async def auth_client(app):
    """Cliente HTTP con una IP de origen unica por test.

    El contrato fija un rate limit de 3 req/min por IP (ADR-0019). Para que cada
    test parta de un presupuesto limpio e independiente (sin verse afectado por
    las peticiones de los demas tests), cada test se ejecuta desde una IP distinta.
    Sigue siendo caja negra: solo se varia la IP de origen de la peticion HTTP.
    """
    import httpx
    from httpx import ASGITransport

    host = f"test-{uuid.uuid4().hex}"
    transport = ASGITransport(app=app, client=(host, 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# ---------------------------------------------------------------------------
# Helpers de bus de eventos (RabbitMQ) — interfaz observable 3.6
# ---------------------------------------------------------------------------
async def _rabbit_queue():
    import aio_pika

    url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()
    queue = await channel.declare_queue(COLA_EMAIL_AUTH, durable=False)
    return connection, channel, queue


async def consume_activation_event(timeout: float = 10.0) -> dict:
    """Consume un unico mensaje de la cola `email.auth` y devuelve su JSON."""
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


async def register(client, email: str):
    return await client.post(REGISTRO, json={"email": email})


async def register_and_get_token(client, email: str | None = None):
    email = email or unique_email()
    response = await register(client, email)
    assert response.status_code == 200, f"Registro esperaba 200, obtuvo {response.status_code}: {response.text}"
    event = await consume_activation_event(timeout=10.0)
    return email, event


# ===========================================================================
# 3.1 Solicitud de Autoregistro
# ===========================================================================
class TestRegistro:
    async def test_camino_feliz_email_nuevo_retorna_200_mensaje_generico(self, auth_client):
        response = await register(auth_client, unique_email())
        assert response.status_code == 200, response.text
        assert response.json() == {"message": MSG_REGISTRO}

    async def test_email_duplicado_retorna_mismo_json_y_tiempo_similar(self, auth_client):
        email = unique_email()

        t0 = time.monotonic()
        r1 = await register(auth_client, email)
        t1 = time.monotonic()
        r2 = await register(auth_client, email)
        t2 = time.monotonic()

        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200, r2.text
        assert r1.json() == {"message": MSG_REGISTRO}
        assert r2.json() == {"message": MSG_REGISTRO}
        assert r1.json() == r2.json(), "El cuerpo debe ser identico (anti-enumeracion)"

        delta_nuevo = t1 - t0
        delta_dup = t2 - t1
        # Mejor-esfuerzo: evita divergencias groseras de tiempo (timing attack).
        assert abs(delta_nuevo - delta_dup) < 2.0, (
            f"Divergencia de tiempo sospechosa: nuevo={delta_nuevo:.3f}s dup={delta_dup:.3f}s"
        )

    async def test_cooldown_activo_no_reencola_segundo_evento(self, auth_client):
        await purge_activation_queue()
        email = unique_email()

        await register(auth_client, email)
        await register(auth_client, email)

        first = await consume_activation_event(timeout=10.0)
        assert first["payload"]["email"] == email

        with pytest.raises(asyncio.TimeoutError):
            await consume_activation_event(timeout=2.0)

    async def test_email_invalido_retorna_422(self, auth_client):
        response = await register(auth_client, "correo_sin_dominio.com")
        assert response.status_code == 422, response.text
        assert response.json() == {"detail": MSG_EMAIL_INVALIDO}

    async def test_payload_vacio_retorna_422(self, auth_client):
        response = await auth_client.post(REGISTRO, json={})
        assert response.status_code == 422, response.text

    async def test_campo_email_ausente_retorna_422(self, auth_client):
        response = await auth_client.post(REGISTRO, json={"correo": "cliente@ejemplo.com"})
        assert response.status_code == 422, response.text

    async def test_email_vacio_retorna_422(self, auth_client):
        response = await auth_client.post(REGISTRO, json={"email": ""})
        assert response.status_code == 422, response.text

    async def test_rate_limit_excedido_retorna_429(self, auth_client):
        # El contrato (ADR-0019) fija maximo 3 peticiones por minuto por IP.
        # Se usan emails invalidos (validacion Pydantic, sin tocar DB) para no depender
        # de la infraestructura y aislar el comportamiento del rate limiter.
        for _ in range(3):
            response = await register(auth_client, "correo_invalido")
            assert response.status_code == 422, response.text
        response = await register(auth_client, "correo_invalido")
        assert response.status_code == 429, response.text
        assert response.json() == {"detail": MSG_RATE_LIMIT}


# ===========================================================================
# 3.2 Activacion de Cuenta
# ===========================================================================
class TestActivacion:
    async def test_camino_feliz_token_valido_retorna_200(self, auth_client):
        email, event = await register_and_get_token(auth_client)
        token = event["payload"]["token"]

        response = await auth_client.post(ACTIVAR, json={"token": token, "password": PASSWORD_OK})
        assert response.status_code == 200, response.text
        assert response.json() == {"message": MSG_ACTIVACION_OK}

    async def test_token_inexistente_retorna_400(self, auth_client):
        token = str(uuid.uuid4())
        response = await auth_client.post(ACTIVAR, json={"token": token, "password": PASSWORD_OK})
        assert response.status_code == 400, response.text
        assert response.json() == {"detail": MSG_ACTIVACION_INVALIDO}

    async def test_token_formato_invalido_retorna_400(self, auth_client):
        response = await auth_client.post(ACTIVAR, json={"token": "token-alterado", "password": PASSWORD_OK})
        assert response.status_code == 400, response.text
        assert response.json() == {"detail": MSG_ACTIVACION_INVALIDO}

    async def test_password_debil_retorna_422_y_no_marca_token(self, auth_client):
        email, event = await register_and_get_token(auth_client)
        token = event["payload"]["token"]

        weak = await auth_client.post(ACTIVAR, json={"token": token, "password": PASSWORD_DEBIL})
        assert weak.status_code == 422, weak.text
        assert weak.json() == {"detail": MSG_PASSWORD_DEBIL}

        # El token NO se marca como usado: la misma activacion con password valida funciona.
        ok = await auth_client.post(ACTIVAR, json={"token": token, "password": PASSWORD_OK})
        assert ok.status_code == 200, ok.text
        assert ok.json() == {"message": MSG_ACTIVACION_OK}

    async def test_token_ya_usado_retorna_400(self, auth_client):
        email, event = await register_and_get_token(auth_client)
        token = event["payload"]["token"]

        first = await auth_client.post(ACTIVAR, json={"token": token, "password": PASSWORD_OK})
        assert first.status_code == 200, first.text

        second = await auth_client.post(ACTIVAR, json={"token": token, "password": PASSWORD_OK})
        assert second.status_code == 400, second.text
        assert second.json() == {"detail": MSG_ACTIVACION_INVALIDO}

    @pytest.mark.skip(reason="NO VERIFICADO: no hay forma observable de crear un token con expira_en en el pasado (la API siempre genera expiracion de 24h).")
    async def test_token_expirado_retorna_400(self, auth_client):
        ...


# ===========================================================================
# 3.3 Autenticacion / Login
# ===========================================================================
class TestLogin:
    async def _usuario_activo(self, auth_client):
        email, event = await register_and_get_token(auth_client)
        token = event["payload"]["token"]
        r = await auth_client.post(ACTIVAR, json={"token": token, "password": PASSWORD_OK})
        assert r.status_code == 200, r.text
        return email

    async def test_camino_feliz_retorna_jwt_con_payload(self, auth_client):
        email = await self._usuario_activo(auth_client)

        response = await auth_client.post(LOGIN, json={"email": email, "password": PASSWORD_OK})
        assert response.status_code == 200, response.text
        body = response.json()

        assert set(body.keys()) == {"access_token", "token_type", "expires_in", "usuario"}
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 3600
        assert isinstance(body["access_token"], str) and len(body["access_token"]) > 0

        usuario = body["usuario"]
        assert usuario["email"] == email
        assert usuario["rol"] == "cliente"
        assert isinstance(usuario["id"], int)

    async def test_password_incorrecta_retorna_401(self, auth_client):
        email = await self._usuario_activo(auth_client)

        response = await auth_client.post(LOGIN, json={"email": email, "password": "WrongPass123!"})
        assert response.status_code == 401, response.text
        assert response.json() == {"detail": MSG_LOGIN_FALLO}

    async def test_cuenta_no_activada_retorna_401(self, auth_client):
        email = unique_email()
        r = await register(auth_client, email)
        assert r.status_code == 200
        # Drenar el evento publicado para no contaminar la cola
        await consume_activation_event(timeout=10.0)

        response = await auth_client.post(LOGIN, json={"email": email, "password": PASSWORD_OK})
        assert response.status_code == 401, response.text
        assert response.json() == {"detail": MSG_LOGIN_FALLO}

    async def test_email_inexistente_retorna_401(self, auth_client):
        response = await auth_client.post(LOGIN, json={"email": unique_email(), "password": PASSWORD_OK})
        assert response.status_code == 401, response.text
        assert response.json() == {"detail": MSG_LOGIN_FALLO}

    @pytest.mark.skip(reason="NO VERIFICADO: no hay endpoint observable para suspender una cuenta; requiere manipulacion directa de DB.")
    async def test_cuenta_suspendida_retorna_403(self, auth_client):
        response = await auth_client.post(LOGIN, json={"email": unique_email(), "password": PASSWORD_OK})
        assert response.status_code == 403
        assert response.json() == {"detail": MSG_SUSPENDIDA}


# ===========================================================================
# 3.4 Inspeccion de Sesion Activa (/me)
# ===========================================================================
class TestMe:
    async def test_camino_feliz_token_valido_retorna_perfil(self, auth_client):
        email, event = await register_and_get_token(auth_client)
        token = event["payload"]["token"]
        r = await auth_client.post(ACTIVAR, json={"token": token, "password": PASSWORD_OK})
        assert r.status_code == 200, r.text

        login = await auth_client.post(LOGIN, json={"email": email, "password": PASSWORD_OK})
        assert login.status_code == 200, login.text
        access_token = login.json()["access_token"]

        response = await auth_client.get(ME, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 200, response.text
        body = response.json()
        assert set(body.keys()) == {"id", "email", "rol", "estado"}
        assert body["email"] == email
        assert body["rol"] == "cliente"
        assert body["estado"] == "activo"

    async def test_token_ausente_retorna_401(self, auth_client):
        response = await auth_client.get(ME)
        assert response.status_code == 401, response.text
        assert response.json() == {"detail": MSG_NO_AUTENTICADO}

    async def test_token_malformado_retorna_401(self, auth_client):
        response = await auth_client.get(ME, headers={"Authorization": "Bearer token-corrupto"})
        assert response.status_code == 401, response.text
        assert response.json() == {"detail": MSG_NO_AUTENTICADO}

    @pytest.mark.skip(reason="NO VERIFICADO: no hay forma observable de emitir un JWT con exp vencido sin esperar 1 hora o manipular la DB/clave.")
    async def test_token_expirado_retorna_401(self, auth_client):
        ...


# ===========================================================================
# 3.6 Evento de Correo en RabbitMQ
# ===========================================================================
class TestEventoRabbitMQ:
    async def test_registro_publica_evento_activacion_en_cola_email_auth(self, auth_client):
        await purge_activation_queue()
        email = unique_email()

        r = await register(auth_client, email)
        assert r.status_code == 200, r.text

        event = await consume_activation_event(timeout=10.0)

        assert event["evento"] == EVENTO_ACTIVACION

        # correlation_id presente con formato UUID
        correlation_id = event.get("correlation_id")
        assert correlation_id and isinstance(correlation_id, str)
        uuid.UUID(correlation_id)

        # timestamp presente (ISO-8601)
        assert "timestamp" in event and event["timestamp"]

        payload = event["payload"]
        assert payload["email"] == email

        token = payload["token"]
        token_uuid = uuid.UUID(token)
        assert str(token_uuid) == token, "El token debe ser UUID v4 canonico"

        url = payload["url_activacion"]
        assert f"/activar?token={token}" in url

        assert "expira_en" in payload and payload["expira_en"]
