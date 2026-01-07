"""High-level ingestion orchestration for tests and API endpoints."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any

from app.schemas import ParsedChunk, ParserOutput
from ingestion.base import BaseParser


if TYPE_CHECKING:
    from app.memory import MemoryAgent
    from app.schemas.base import SourceType


class IngestionService:
    """Convert uploaded content into ParserOutput and index it via MemoryAgent."""

    def __init__(
        self,
        *,
        memory_agent: MemoryAgent,
        parser: BaseParser | None = None,
    ) -> None:
        self._memory = memory_agent
        self._parser = parser or BaseParser()

    async def ingest_document(
        self,
        *,
        content: bytes | str,
        filename: str,
        source_id: str | None = None,
        source_type: SourceType = "local",
        source_url: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> ParserOutput:
        """Parse and index the provided content."""

        metadata: dict[str, Any] = {
            "filename": filename,
            "source_type": source_type,
            "source_url": source_url,
        }
        if extra_metadata:
            metadata.update(extra_metadata)

        start = time.perf_counter()
        chunks = self._parser.parse(content, metadata)
        parser_output = _build_parser_output(chunks, metadata)

        # Store chunks in memory agent
        await self._memory.add_documents(
            chunks=parser_output.chunks,
            source_metadata={
                "source_id": source_id or parser_output.document_id,
                "source_type": source_type,
                "source_url": source_url,
                "url": source_url,  # MemoryAgent expects "url" key
                "filename": filename,
                **(extra_metadata or {}),
            },
        )

        return parser_output.model_copy(
            update={
                "processing_time_ms": round((time.perf_counter() - start) * 1000, 2)
            }
        )


def _build_parser_output(
    chunks: list[ParsedChunk],
    metadata: dict[str, Any],
) -> ParserOutput:
    document_id = metadata.get("document_id") or str(uuid.uuid4())
    return ParserOutput(
        document_id=document_id,
        metadata=dict(metadata),
        chunks=chunks,
        total_pages=max(1, len(chunks)),
        processing_time_ms=0.0,
    )


__all__ = ["IngestionService"]
