"""API-specific schemas for FastAPI routes.

These models wrap the authoritative agent schemas for HTTP requests/responses.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.base import Persona


class HealthStatus(BaseModel):
    """Response body for the /health endpoint."""

    db: Literal["connected", "degraded", "offline"]
    agents: Literal["ready", "initializing", "degraded"]


class QueryRequest(BaseModel):
    """Request body for the /query endpoint."""

    text: str = Field(..., min_length=1, description="User's natural language query")
    persona: Persona = Field(
        default="General", description="Persona driving the tailoring tone"
    )
    stream: bool = Field(
        default=False,
        description="When true, the response is streamed via Server-Sent Events",
    )


class StreamEvent(BaseModel):
    """A single Server-Sent Event envelope."""

    event: Literal["token", "complete"]
    data: dict[str, Any] | str


class IngestResponse(BaseModel):
    """Acknowledgement returned by /ingest uploads."""

    task_id: str
    filename: str
    status: Literal["queued", "processing", "completed"]
