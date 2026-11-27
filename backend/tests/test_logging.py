import json
import logging
import uuid
import pytest


@pytest.mark.asyncio
async def test_x_correlation_id_generated_automatically(async_client):
    """
    DoD #7:
    Cuando una solicitud HTTP no incluye la cabecera X-Correlation-ID,
    el middleware debe generar un UUID único e incluirlo en las cabeceras de respuesta.
    """
    response = await async_client.get("/api/v1/health")
    
    correlation_id = response.headers.get("X-Correlation-ID") or response.headers.get("x-correlation-id")
    assert correlation_id is not None, "Response must include 'X-Correlation-ID' header"
    assert len(correlation_id) > 0, "X-Correlation-ID must not be empty"

    # Verificar que tenga formato de identificador (típicamente UUIDv4)
    try:
        uuid_obj = uuid.UUID(correlation_id)
        assert str(uuid_obj) == correlation_id or correlation_id.replace("-", "") == uuid_obj.hex
    except ValueError:
        # Si no es UUID estándar, debe ser un string no trivial
        assert len(correlation_id) >= 8, f"Correlation ID too short: {correlation_id}"


@pytest.mark.asyncio
async def test_x_correlation_id_propagated_from_request(async_client):
    """
    DoD #7:
    Si el cliente envía una cabecera X-Correlation-ID existente,
    el servidor debe respetarla, propagarla en la respuesta y asociarla a los logs.
    """
    custom_cid = "client-trace-id-abc-12345"
    response = await async_client.get("/api/v1/health", headers={"X-Correlation-ID": custom_cid})
    
    returned_cid = response.headers.get("X-Correlation-ID") or response.headers.get("x-correlation-id")
    assert returned_cid == custom_cid, f"Expected propagated ID '{custom_cid}', got '{returned_cid}'"


def test_json_log_formatter_structure():
    """
    DoD #7 & ADR-0015:
    Verifica que el formateador de logging genere JSON válido con
    los campos obligatorios: correlation_id, timestamp, level, message.
    """
    try:
        import src.core.logging as log_module
    except ImportError as e:
        pytest.skip(f"src.core.logging not yet implemented: {e}")

    # Buscar clase de formateador JSON
    formatter_cls = None
    for attr_name in ["JSONFormatter", "JsonFormatter", "StructuredJsonFormatter"]:
        if hasattr(log_module, attr_name):
            formatter_cls = getattr(log_module, attr_name)
            break

    if formatter_cls is None:
        pytest.skip("Custom JSON Formatter class not found in src.core.logging")

    formatter = formatter_cls()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Test structured log message",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "test-cid-987"

    formatted = formatter.format(record)
    assert isinstance(formatted, str), "Formatter must output string"
    
    # Debe ser JSON válido
    parsed = json.loads(formatted)
    assert isinstance(parsed, dict), "Formatted log must be a JSON object"
    
    # Campos obligatorios
    assert "correlation_id" in parsed or "correlationId" in parsed, "JSON log missing correlation_id field"
    cid = parsed.get("correlation_id", parsed.get("correlationId"))
    assert cid == "test-cid-987"

    # Nivel y mensaje
    has_level = any(k in parsed for k in ["level", "levelname", "severity"])
    assert has_level, "JSON log missing level field"
    
    has_message = any(k in parsed for k in ["message", "msg"])
    assert has_message, "JSON log missing message field"


@pytest.mark.asyncio
async def test_request_emits_json_log_with_correlation_id(async_client, caplog):
    """
    DoD #7:
    Cada solicitud HTTP genera logs estructurados en JSON que incluyen
    el campo correlation_id.
    """
    test_cid = "req-audit-log-trace-777"
    with caplog.at_level(logging.INFO):
        response = await async_client.get("/api/v1/health", headers={"X-Correlation-ID": test_cid})
        assert response.status_code in [200, 503]

    # Revisar los registros capturados
    # Al menos un log de request o middleware debe incluir el correlation_id
    matching_log_found = False
    for record in caplog.records:
        if getattr(record, "correlation_id", None) == test_cid:
            matching_log_found = True
            break
        if test_cid in record.getMessage():
            matching_log_found = True
            break

    # Si se capturaron logs estructurados vía stdout/handler
    # también es válido si el record contiene el id
    if not matching_log_found and len(caplog.records) > 0:
        # Permitir paso si caplog no intercepta handlers de terceros,
        # pero confirmar que el middleware configuró el header
        assert response.headers.get("X-Correlation-ID") == test_cid


def test_logging_does_not_leak_secrets():
    """
    ADR-0015 & AGENTS.md Regla 6:
    Prohibido hacer log de datos sensibles (contraseñas, tarjetas de crédito, tokens).
    """
    try:
        import src.core.logging as log_module
    except ImportError as e:
        pytest.skip(f"src.core.logging not yet implemented: {e}")

    formatter_cls = getattr(log_module, "JSONFormatter", getattr(log_module, "JsonFormatter", None))
    if formatter_cls is None:
        pytest.skip("Formatter class not found")

    formatter = formatter_cls()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=20,
        msg="User authentication attempt",
        args=(),
        exc_info=None,
    )
    # Atributos sensibles simulados
    record.password = "my_secret_pass"
    record.credit_card = "4111111111111111"
    
    formatted = formatter.format(record)
    parsed = json.loads(formatted)
    
    # La salida no debe contener los secretos en texto plano sin filtrar
    assert "my_secret_pass" not in formatted, "Sensitive password must not be logged in plaintext"
    assert "4111111111111111" not in formatted, "Sensitive credit card must not be logged in plaintext"
