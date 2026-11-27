"""Cliente HTTP de Stripe Sandbox y verificacion de firma de webhook (ADR-0013).

No se usa el SDK de Stripe: las dos operaciones necesarias se resuelven con httpx
(ya disponible) y HMAC-SHA256 nativo. Nunca se envian, persisten ni loguean datos
de tarjeta: solo identificadores de Stripe y la clave de idempotencia.
"""

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from typing import Optional

import httpx

from src.config import get_settings

TEST_WEBHOOK_SECRET = "whsec_test"
WEBHOOK_TOLERANCE_SECONDS = 300
PLACEHOLDER_PREFIX = "REEMPLAZAR"


@dataclass(frozen=True)
class PaymentIntentData:
    payment_intent_id: str
    client_secret: str


class StripeGatewayError(Exception):
    """Fallo al contactar con Stripe; nunca incluye datos de tarjeta."""


def _using_real_stripe(secret_key: str) -> bool:
    return bool(secret_key) and PLACEHOLDER_PREFIX not in secret_key


def idempotency_key(carrito_id: int, intento: int) -> str:
    return f"pedido-{carrito_id}-{intento}"


async def create_payment_intent(
    carrito_id: int, intento: int, monto: float, moneda: str = "PEN"
) -> PaymentIntentData:
    """Crea un PaymentIntent en modo test.

    Sin una clave de prueba configurada se genera un identificador local
    determinista de sandbox para permitir el flujo completo sin contactar a
    Stripe. Con clave configurada se usa la API HTTP de Stripe con la clave de
    idempotencia `pedido-{carrito_id}-{intento}`.
    """
    settings = get_settings()
    key = idempotency_key(carrito_id, intento)
    if not _using_real_stripe(settings.stripe_secret_key):
        suffix = uuid.uuid4().hex
        return PaymentIntentData(
            payment_intent_id=f"pi_test_{suffix}",
            client_secret=f"pi_test_{suffix}_secret_{uuid.uuid4().hex[:12]}",
        )

    data = {
        "amount": str(int(round(float(monto) * 100))),
        "currency": moneda.lower(),
        "automatic_payment_methods[enabled]": "true",
        "metadata[carrito_id]": str(carrito_id),
        "metadata[intento]": str(intento),
    }
    headers = {
        "Authorization": f"Bearer {settings.stripe_secret_key}",
        "Idempotency-Key": key,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{settings.stripe_api_url.rstrip('/')}/payment_intents",
                data=data,
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()
        return PaymentIntentData(
            payment_intent_id=str(body["id"]),
            client_secret=str(body["client_secret"]),
        )
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise StripeGatewayError("No se pudo iniciar el pago con Stripe.") from exc


def verify_webhook_signature(payload: bytes, signature_header: Optional[str]) -> bool:
    """Verifica Stripe-Signature (t=,v1=) con HMAC-SHA256 y tolerancia de 5 min."""
    if not signature_header:
        return False
    settings = get_settings()
    secret = settings.stripe_webhook_secret
    if not secret:
        if settings.app_env == "production":
            return False
        secret = TEST_WEBHOOK_SECRET

    timestamp: Optional[int] = None
    signatures: list[str] = []
    for part in signature_header.split(","):
        name, sep, value = part.strip().partition("=")
        if not sep:
            continue
        if name == "t":
            try:
                timestamp = int(value)
            except ValueError:
                return False
        elif name == "v1":
            signatures.append(value)
    if timestamp is None or not signatures:
        return False
    if abs(int(time.time()) - timestamp) > WEBHOOK_TOLERANCE_SECONDS:
        return False

    signed = f"{timestamp}.".encode() + payload
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, candidate) for candidate in signatures)


def parse_webhook_event(payload: bytes) -> dict:
    """Parsea el evento; lanza ValueError si el JSON no es valido."""
    event = json.loads(payload.decode("utf-8"))
    if not isinstance(event, dict):
        raise ValueError("evento no valido")
    return event
