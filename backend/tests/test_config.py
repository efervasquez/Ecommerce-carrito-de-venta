import os
from unittest.mock import patch
import pytest

try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings
    except ImportError:
        BaseSettings = object


def test_settings_loads_from_environment_variables(monkeypatch):
    """
    DoD #8:
    Valida que los settings de la aplicación se carguen correctamente
    a través de variables de entorno utilizando Pydantic Settings.
    """
    test_env = {
        "MYSQL_HOST": "192.168.1.100",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "custom_user",
        "MYSQL_PASSWORD": "custom_password_xyz",
        "MYSQL_DB": "custom_botica_db",
        "RABBITMQ_URL": "amqp://testadmin:secret@broker-host:5672//",
        "LOG_LEVEL": "DEBUG",
        "CORS_ORIGINS": "http://localhost:3000,http://localhost:5173",
        "ENVIRONMENT": "development",
    }
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)

    try:
        import src.config as config_module
    except ImportError as e:
        pytest.skip(f"src.config not yet implemented: {e}")

    # Cargar settings (soporta tanto get_settings() como Settings())
    settings = None
    if hasattr(config_module, "get_settings"):
        settings = config_module.get_settings()
    elif hasattr(config_module, "Settings"):
        settings = config_module.Settings()

    assert settings is not None, "Could not obtain Settings instance from src.config"

    # Verificar que herede de BaseSettings
    if BaseSettings is not object:
        assert isinstance(settings, BaseSettings), "Settings class must inherit from BaseSettings"

    # Validar que los valores coincidan con las variables inyectadas
    if hasattr(settings, "MYSQL_HOST"):
        assert settings.MYSQL_HOST == "192.168.1.100"
    elif hasattr(settings, "mysql_host"):
        assert settings.mysql_host == "192.168.1.100"

    if hasattr(settings, "LOG_LEVEL"):
        assert settings.LOG_LEVEL == "DEBUG"
    elif hasattr(settings, "log_level"):
        assert settings.log_level == "DEBUG"

    if hasattr(settings, "RABBITMQ_URL"):
        assert "broker-host" in str(settings.RABBITMQ_URL)
    elif hasattr(settings, "rabbitmq_url"):
        assert "broker-host" in str(settings.rabbitmq_url)


def test_settings_no_hardcoded_credentials_in_source():
    """
    DoD #8 & AGENTS.md Regla 8 (Seguridad):
    Queda terminantemente prohibido escribir credenciales en texto plano
    en el código fuente. Las variables sensibles deben requerir configuración
    o tener valores solo para testing/local.
    """
    try:
        import src.config as config_module
    except ImportError as e:
        pytest.skip(f"src.config not yet implemented: {e}")

    # Verificar que el archivo config.py no contenga passwords de producción embebidos
    config_file_path = config_module.__file__
    with open(config_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    prohibited_strings = ["root_password", "prod_secret", "SuperSecret123!"]
    for s in prohibited_strings:
        assert s not in content, f"Hardcoded credential detected in config file: {s}"


def test_settings_override_via_monkeypatch(monkeypatch):
    """
    Verifica que al cambiar dinámicamente una variable de entorno,
    la configuración refleje el cambio.
    """
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    
    try:
        import src.config as config_module
        if hasattr(config_module, "Settings"):
            # Instanciar nueva instancia limpia
            custom_settings = config_module.Settings()
            log_level = getattr(custom_settings, "LOG_LEVEL", getattr(custom_settings, "log_level", None))
            assert log_level == "WARNING", f"Expected LOG_LEVEL 'WARNING', got {log_level}"
    except ImportError as e:
        pytest.skip(f"src.config not yet implemented: {e}")
