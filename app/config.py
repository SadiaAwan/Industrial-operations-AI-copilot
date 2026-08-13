"""Environment-driven application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg://copilot:copilot@localhost:5432/copilot"
    )
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_timeout_seconds: int = Field(default=30, ge=1, le=120)
    runtime_mode: Literal["unconfigured", "mock"] = "unconfigured"
    mlflow_tracking_uri: str | None = None
    mlflow_experiment_name: str = "industrial-operations-copilot"
    mlflow_langchain_autolog: bool = True
    mlflow_database_name: str = Field(
        default="mlflow", pattern=r"^[a-z][a-z0-9_]{0,62}$"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
