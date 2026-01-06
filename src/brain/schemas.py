"""Brain (RAG Engine) schemas for query processing and answer generation.

Reference: Phase 2-2 RAG Engine Implementation
Aligned with: docs/02_AGENT_SPECS.md (Memory Agent, Tailor Agent schemas)
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# Type alias matching docs/02_AGENT_SPECS.md
Persona = Literal["Technical", "Executive", "General"]


class RAGErrorCodes:
    """Error codes specific to the RAG Engine."""

    RETRIEVAL_FAILED = "ERR_RAG_RETRIEVAL_FAILED"
    NO_RELEVANT_CONTEXT = "ERR_RAG_NO_RELEVANT_CONTEXT"
    LLM_FAILED = "ERR_RAG_LLM_FAILED"
    CONTEXT_TOO_LARGE = "ERR_RAG_CONTEXT_TOO_LARGE"
    INVALID_QUERY = "ERR_RAG_INVALID_QUERY"


class RAGFailure(BaseModel):
    """Standardized error object for RAG Engine failures."""

    agent_id: str = "rag_engine"
    error_code: str
    message: str
    recoverable: bool = False
    details: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ContextNode(BaseModel):
    """A single piece of retrieved context from the vector store.

    Aligned with RetrievedContext from docs/02_AGENT_SPECS.md Section 2.3
    """

    id: str = Field(..., description="Chunk ID")
    text: str = Field(..., description="The text content")
    score: float = Field(..., description="Relevance score from vector search")
    source_id: str = Field(default="", description="Source document ID")
    source_url: str | None = Field(default=None, description="URL if web-based")
    metadata: dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    """A citation linking an answer to its source.

    Aligned with SourceCitation from docs/02_AGENT_SPECS.md Section 2.4
    """

    source_id: str
    chunk_id: str
    text_snippet: str = Field(..., description="The exact text snippet used")
    url: str | None = None


class Answer(BaseModel):
    """The generated answer with citations and metadata.

    Aligned with TailorOutput from docs/02_AGENT_SPECS.md Section 2.4
    """

    content: str = Field(..., description="The synthesized response")
    citations: list[Citation] = Field(default_factory=list)
    tone_used: str = Field(default="General", description="Persona tone applied")
    follow_up_suggestions: list[str] = Field(default_factory=list)
    confidence_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence in answer quality"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrieveConfig(BaseModel):
    """Configuration for the retrieve operation.

    Aligned with MemoryQuery from docs/02_AGENT_SPECS.md Section 2.3
    """

    top_k: int = Field(default=5, ge=1, le=100)
    min_score: float = Field(
        default=0.7, ge=0.0, le=1.0, description="min_relevance_score"
    )
    filters: dict[str, Any] | None = None


class GenerateConfig(BaseModel):
    """Configuration for answer generation.

    Aligned with TailorInput from docs/02_AGENT_SPECS.md Section 2.4
    """

    max_context_tokens: int = Field(default=4000, ge=100, le=32000)
    include_citations: bool = True
    persona: Persona = Field(default="General", description="Output tone/style")
    system_prompt: str | None = None
    formatting_instructions: str | None = None


class QueryConfig(BaseModel):
    """Combined configuration for the full query pipeline."""

    retrieve: RetrieveConfig = Field(default_factory=RetrieveConfig)
    generate: GenerateConfig = Field(default_factory=GenerateConfig)


class QueryResult(BaseModel):
    """Result of a full RAG query operation."""

    answer: Answer
    context_used: list[ContextNode]
    retrieval_count: int
    filtered_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)
