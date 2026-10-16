import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Ensure backend directory is in sys.path so 'src' is importable
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="session")
def default_env():
    """Sets standard testing environment variables."""
    test_env = {
        "MYSQL_HOST": "127.0.0.1",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "test_user",
        "MYSQL_PASSWORD": "test_password",
        "MYSQL_DB": "test_botica",
        "DATABASE_URL": "mysql+aiomysql://test_user:test_password@127.0.0.1:3306/test_botica",
        "RABBITMQ_URL": "amqp://guest:guest@localhost:5672/",
        "LOG_LEVEL": "INFO",
        "CORS_ORIGINS": "http://localhost:5173",
        "ENVIRONMENT": "testing",
    }
    with patch.dict(os.environ, test_env, clear=False):
        yield test_env


@pytest.fixture
def app(default_env):
    """Loads FastAPI application instance."""
    try:
        from src.main import app as fastapi_app
        return fastapi_app
    except ImportError as e:
        pytest.skip(f"Backend application (src.main.app) not yet implemented: {e}")


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator:
    """Async HTTP client for testing FastAPI endpoints via ASGI."""
    import httpx

    try:
        from httpx import ASGITransport
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    except (ImportError, TypeError):
        async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
            yield client


@pytest.fixture
def client(app) -> Generator:
    """Synchronous TestClient for FastAPI endpoints."""
    from fastapi.testclient import TestClient
    with TestClient(app=app, base_url="http://testserver") as test_client:
        yield test_client


@pytest.fixture
def mock_db_healthy():
    """Helper mock to simulate healthy database connection."""
    mock = AsyncMock()
    mock.return_value = True
    return mock


@pytest.fixture
def mock_db_unhealthy():
    """Helper mock to simulate database failure or disconnection."""
    mock = AsyncMock()
    mock.side_effect = Exception("Database connection refused: MySQL92 unreachable")
    return mock


@pytest.fixture
def mock_rabbitmq_healthy():
    """Helper mock to simulate healthy RabbitMQ connection."""
    mock = AsyncMock()
    mock.return_value = True
    return mock


@pytest.fixture
def mock_rabbitmq_unhealthy():
    """Helper mock to simulate RabbitMQ connection failure."""
    mock = AsyncMock()
    mock.side_effect = Exception("RabbitMQ connection refused on localhost:5672")
    return mock
