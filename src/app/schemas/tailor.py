"""Tailor Agent schemas.

Reference: docs/02_AGENT_SPECS.md Section 2.4
"""

from pydantic import BaseModel, Field

from app.schemas.base import Persona
from app.schemas.memory import RetrievedContext


class SourceCitation(BaseModel):
    """Citation for a source used in the response."""

    source_id: str
    chunk_id: str
    text_snippet: str
    url: str | None = None


class TailorInput(BaseModel):
    """Input for the Tailor Agent."""

    user_query: str
    context_chunks: list[RetrievedContext]
    persona: Persona = "General"
    formatting_instructions: str | None = None


class TailorOutput(BaseModel):
    """Output from the Tailor Agent."""

    content: str = Field(..., description="The synthesized response")
    citations: list[SourceCitation]
    tone_used: str
    follow_up_suggestions: list[str]
    confidence_score: float
