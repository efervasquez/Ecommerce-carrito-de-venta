import json
from functools import lru_cache
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: Union[List[str], str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        alias="CORS_ORIGINS",
    )

    # MySQL Database Settings
    mysql_host: str = Field(default="127.0.0.1", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: str = Field(default="ecommerce_user", alias="MYSQL_USER")
    mysql_password: str = Field(default="ecommerce_pass", alias="MYSQL_PASSWORD")
    mysql_db: str = Field(default="ecommerce_botica", alias="MYSQL_DB")
    mysql_pool_size: int = Field(default=10, alias="MYSQL_POOL_SIZE")
    mysql_max_overflow: int = Field(default=5, alias="MYSQL_MAX_OVERFLOW")

    # RabbitMQ Settings
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/", alias="RABBITMQ_URL"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_trimmed = v.strip()
            if v_trimmed.startswith("[") and v_trimmed.endswith("]"):
                try:
                    return json.loads(v_trimmed)
                except Exception:
                    pass
            return [origin.strip() for origin in v_trimmed.split(",") if origin.strip()]
        return v

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@"
            f"{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
