"""Application configuration powered by pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """Runtime configuration for the FastAPI application."""

    app_name: str = Field(default="ROMA RAG API", alias="APP_NAME")
    ingest_auth_token: str = Field(
        default="local-dev-token",
        alias="API_INGEST_TOKEN",
        description="Bearer token required for /ingest uploads",
    )
    ingest_auth_enabled: bool = Field(
        default=True,
        alias="INGEST_AUTH_ENABLED",
        description="When false, /ingest accepts requests without auth",
    )
    ingest_ocr_enabled: bool = Field(
        default=False,
        alias="INGEST_OCR_ENABLED",
        description="Enable OCR for scanned PDFs during ingestion",
    )
    stream_chunk_pause_ms: int = Field(
        default=0,
        alias="STREAM_CHUNK_PAUSE_MS",
        description="Artificial delay between streamed tokens (useful for demos/tests)",
    )

    # LLM Configuration
    llm_provider: Literal["openai", "anthropic"] = Field(
        default="openai",
        alias="LLM_PROVIDER",
        description="LLM provider to use (openai or anthropic)",
    )
    llm_model: str = Field(
        default="gpt-4o",
        alias="LLM_MODEL",
        description="Model name (e.g., gpt-4o, claude-sonnet-3.5)",
    )
    openai_api_key: str = Field(
        default="",
        alias="OPENAI_API_KEY",
        description="OpenAI API key",
    )
    anthropic_api_key: str = Field(
        default="",
        alias="ANTHROPIC_API_KEY",
        description="Anthropic API key",
    )
    llm_max_retries: int = Field(
        default=3,
        alias="LLM_MAX_RETRIES",
        description="Maximum retry attempts for LLM requests",
    )
    llm_timeout_seconds: int = Field(
        default=30,
        alias="LLM_TIMEOUT_SECONDS",
        description="Timeout for LLM requests in seconds",
    )
    llm_temperature: float = Field(
        default=0.7,
        alias="LLM_TEMPERATURE",
        description="Temperature for LLM sampling (0.0-2.0)",
    )
    llm_max_tokens: int = Field(
        default=2048,
        alias="LLM_MAX_TOKENS",
        description="Maximum tokens to generate",
    )

    # Google Drive Configuration
    gdrive_credentials_path: str = Field(
        default="",
        alias="GDRIVE_CREDENTIALS_PATH",
        description="Path to Google Drive service account JSON credentials",
    )
    gdrive_scopes: list[str] = Field(
        default=["https://www.googleapis.com/auth/drive.readonly"],
        alias="GDRIVE_SCOPES",
        description="Google Drive API OAuth scopes",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="RAG_",
        extra="ignore",
    )

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Validate LLM provider is supported."""
        if v not in ("openai", "anthropic"):
            raise ValueError(f"Unsupported LLM provider: {v}")
        return v

    @field_validator("llm_temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is in valid range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {v}")
        return v


@lru_cache(maxsize=1)
def get_settings() -> APISettings:
    """Return a cached settings instance."""

    return APISettings()
