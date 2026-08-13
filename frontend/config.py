"""Environment-driven configuration for the Streamlit frontend."""

from functools import lru_cache
from json import JSONDecodeError, loads
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class FrontendSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="COPILOT_UI_",
        extra="ignore",
    )

    api_base_url: str = "http://localhost:8000"
    api_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    machine_ids: Annotated[tuple[str, ...], NoDecode] = ("P-104", "P-205", "P-307")

    @field_validator("machine_ids", mode="before")
    @classmethod
    def parse_machine_ids(cls, value: object) -> object:
        if isinstance(value, str):
            if value.lstrip().startswith("["):
                try:
                    return loads(value)
                except JSONDecodeError:
                    return value
            return tuple(item.strip() for item in value.split(",") if item.strip())
        return value

    @field_validator("machine_ids")
    @classmethod
    def require_machine_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("at least one machine ID must be configured")
        return value


@lru_cache
def get_frontend_settings() -> FrontendSettings:
    return FrontendSettings()
