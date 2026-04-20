"""Application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    auth_provider: Literal["mock", "firebase"] = "firebase"
    firebase_project_id: str | None = None
    firebase_audience: str | None = None
    callback_secret: str
    export_download_signing_key: str | None = None
    export_download_url_host: str = "downloads.howera.local"
    export_download_url_ttl_minutes: int = Field(default=15, ge=1)

    model_config = SettingsConfigDict(env_prefix="HOWERA_", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
