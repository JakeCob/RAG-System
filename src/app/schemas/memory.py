"""Memory Agent schemas.

Reference: docs/02_AGENT_SPECS.md Section 2.3
"""

from typing import Any

from pydantic import BaseModel, Field


class MemoryQuery(BaseModel):
    """Query input for the Memory Agent."""

    query_text: str
    top_k: int = 5
    min_relevance_score: float = 0.7
    filters: dict[str, Any] | None = Field(
        None, description="Metadata filters (e.g., source_type='gdrive')"
    )


class RetrievedContext(BaseModel):
    """A single retrieved context chunk."""

    chunk_id: str
    content: str
    source_id: str
    source_url: str | None = None
    relevance_score: float
    metadata: dict[str, Any]


class MemoryOutput(BaseModel):
    """Output from the Memory Agent."""

    results: list[RetrievedContext]
    total_found: int
