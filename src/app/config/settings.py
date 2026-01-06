"""Application configuration powered by pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """Runtime configuration for the FastAPI application."""

    app_name: str = Field(default="ROMA RAG API", alias="APP_NAME")
    ingest_auth_token: str = Field(
        default="local-dev-token",
        alias="API_INGEST_TOKEN",
        description="Bearer token required for /ingest uploads",
    )
    stream_chunk_pause_ms: int = Field(
        default=0,
        alias="STREAM_CHUNK_PAUSE_MS",
        description="Artificial delay between streamed tokens (useful for demos/tests)",
    )

    model_config = SettingsConfigDict(env_prefix="RAG_", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> APISettings:
    """Return a cached settings instance."""

    return APISettings()
