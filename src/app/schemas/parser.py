"""Parser Agent (Dolphin) schemas.

Reference: docs/02_AGENT_SPECS.md Section 2.2
"""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.base import FileType, IngestionSource, LayoutType


class ParserInput(BaseModel):
    """Input for the Parser Agent."""

    file_path: str = Field(..., description="Local path or temp URL to the file")
    file_type: FileType
    ingestion_source: IngestionSource  # "gdrive", "local", or "web_scrape"
    force_ocr: bool = False


class ParsedChunk(BaseModel):
    """A single parsed chunk from a document."""

    chunk_id: str
    content: str = Field(
        ..., description="The text content or serialized table markdown"
    )
    chunk_index: int
    page_number: int | None = None
    layout_type: LayoutType
    bbox: list[float] | None = Field(
        None, description="[x1, y1, x2, y2] coordinates if applicable"
    )


class ParserOutput(BaseModel):
    """Output from the Parser Agent."""

    document_id: str
    metadata: dict[str, Any]
    chunks: list[ParsedChunk]
    total_pages: int
    processing_time_ms: float
