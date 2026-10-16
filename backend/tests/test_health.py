import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_health_check_success_returns_200(async_client):
    """
    DoD #2 & #3:
    GET /api/v1/health debe responder HTTP 200 con payload exacto:
    {"status":"ok","mysql":"connected","rabbitmq":"connected"}
    cuando MySQL y RabbitMQ se encuentran activos.
    """
    response = await async_client.get("/api/v1/health")
    
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    data = response.json()
    
    # Validaciones observables estrictas según el contrato en SPRINT0.md / ADR-0004
    assert data.get("status") == "ok", f"Expected status 'ok', got: {data.get('status')}"
    assert data.get("mysql") == "connected", f"Expected mysql 'connected', got: {data.get('mysql')}"
    assert data.get("rabbitmq") == "connected", f"Expected rabbitmq 'connected', got: {data.get('rabbitmq')}"


@pytest.mark.asyncio
async def test_health_check_mysql_failure_returns_503(async_client):
    """
    DoD #3:
    GET /api/v1/health debe responder HTTP 503 cuando la conexión a MySQL falla.
    """
    # Intentamos parchear los puntos comunes donde el servicio/repositorio consulta la BD
    patches = [
        patch("src.modules.health.repository.HealthRepository.check_mysql", new_callable=AsyncMock, side_effect=Exception("MySQL unreachable")),
        patch("src.modules.health.service.HealthService.check_mysql", new_callable=AsyncMock, side_effect=Exception("MySQL unreachable")),
        patch("src.core.database.check_database_connection", new_callable=AsyncMock, side_effect=Exception("MySQL unreachable")),
        patch("src.core.database.ping_db", new_callable=AsyncMock, side_effect=Exception("MySQL unreachable")),
    ]
    
    # Aplicar los patches que existan en el código del DEV
    applied_patches = []
    for p in patches:
        try:
            applied_patches.append(p.start())
        except (AttributeError, ModuleNotFoundError):
            pass

    try:
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 503, f"Expected 503 Service Unavailable on MySQL failure, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") != "ok", "Expected status to indicate failure when MySQL is down"
        assert data.get("mysql") != "connected", "Expected mysql field not to be 'connected' when down"
    finally:
        for p in patches:
            try:
                p.stop()
            except RuntimeError:
                pass


@pytest.mark.asyncio
async def test_health_check_rabbitmq_failure_returns_503(async_client):
    """
    DoD #3:
    GET /api/v1/health debe responder HTTP 503 cuando la conexión a RabbitMQ falla.
    """
    patches = [
        patch("src.modules.health.repository.HealthRepository.check_rabbitmq", new_callable=AsyncMock, side_effect=Exception("RabbitMQ unreachable")),
        patch("src.modules.health.service.HealthService.check_rabbitmq", new_callable=AsyncMock, side_effect=Exception("RabbitMQ unreachable")),
        patch("src.core.broker.check_broker_connection", new_callable=AsyncMock, side_effect=Exception("RabbitMQ unreachable")),
        patch("src.core.broker.ping_broker", new_callable=AsyncMock, side_effect=Exception("RabbitMQ unreachable")),
    ]

    applied_patches = []
    for p in patches:
        try:
            applied_patches.append(p.start())
        except (AttributeError, ModuleNotFoundError):
            pass

    try:
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 503, f"Expected 503 Service Unavailable on RabbitMQ failure, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") != "ok", "Expected status to indicate failure when RabbitMQ is down"
        assert data.get("rabbitmq") != "connected", "Expected rabbitmq field not to be 'connected' when down"
    finally:
        for p in patches:
            try:
                p.stop()
            except RuntimeError:
                pass


@pytest.mark.asyncio
async def test_health_check_both_dependencies_failure_returns_503(async_client):
    """
    DoD #3:
    GET /api/v1/health debe responder HTTP 503 si tanto MySQL como RabbitMQ fallan simultáneamente.
    """
    patches = [
        patch("src.modules.health.repository.HealthRepository.check_mysql", new_callable=AsyncMock, side_effect=Exception("DB Down")),
        patch("src.modules.health.service.HealthService.check_mysql", new_callable=AsyncMock, side_effect=Exception("DB Down")),
        patch("src.modules.health.repository.HealthRepository.check_rabbitmq", new_callable=AsyncMock, side_effect=Exception("Broker Down")),
        patch("src.modules.health.service.HealthService.check_rabbitmq", new_callable=AsyncMock, side_effect=Exception("Broker Down")),
    ]

    for p in patches:
        try:
            p.start()
        except (AttributeError, ModuleNotFoundError):
            pass

    try:
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 503, f"Expected 503 Service Unavailable, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") != "ok"
    finally:
        for p in patches:
            try:
                p.stop()
            except RuntimeError:
                pass
