"""High-level ingestion orchestration for tests and API endpoints."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any

from app.exceptions import AgentFailureError
from app.schemas import AgentFailure, ErrorCodes, ParsedChunk, ParserOutput
from ingestion.base import BaseParser
from ingestion.dolphin import DolphinParser


if TYPE_CHECKING:
    from app.connectors.gdrive import GDriveConnector
    from app.memory import MemoryAgent
    from app.schemas.base import SourceType


class IngestionService:
    """Convert uploaded content into ParserOutput and index it via MemoryAgent."""

    def __init__(
        self,
        *,
        memory_agent: MemoryAgent,
        parser: BaseParser | None = None,
        gdrive_connector: GDriveConnector | None = None,
    ) -> None:
        self._memory = memory_agent
        self._parser = parser or DolphinParser()
        self._gdrive = gdrive_connector

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
        if isinstance(chunks, AgentFailure):
            raise AgentFailureError(
                agent_id=chunks.agent_id,
                error_code=chunks.error_code,
                message=chunks.message,
                recoverable=chunks.recoverable,
                details=chunks.details,
            )
        if not chunks:
            raise AgentFailureError(
                agent_id="parser.dolphin",
                error_code=ErrorCodes.PARSER_INVALID_INPUT,
                message=(
                    "Parser produced no text. The document may be empty or scanned "
                    "without OCR."
                ),
                recoverable=True,
            )
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

    async def ingest_from_gdrive(
        self,
        file_id: str,
        filename: str | None = None,
        source_metadata: dict[str, Any] | None = None,
    ) -> ParserOutput | AgentFailure:
        """Ingest a document from Google Drive.

        Args:
            file_id: Google Drive file ID (from URL).
            filename: Optional override for filename.
            source_metadata: Additional metadata to attach.

        Returns:
            ParserOutput or AgentFailure.
        """
        if self._gdrive is None:
            return AgentFailure(
                agent_id="ingestion_service",
                error_code="ERR_CONNECTOR_NOT_CONFIGURED",
                message="GDrive connector not configured",
                recoverable=False,
                details={"file_id": file_id},
            )

        # Fetch file from Google Drive
        result = await self._gdrive.fetch_file(file_id)

        if isinstance(result, AgentFailure):
            return result

        # Get file metadata if available
        file_content = result
        if filename is None:
            filename = f"gdrive_{file_id}"

        # Build Google Drive URL
        gdrive_url = f"https://drive.google.com/file/d/{file_id}/view"

        # Ingest the fetched content
        metadata = source_metadata or {}
        try:
            return await self.ingest_document(
                content=file_content,
                filename=filename,
                source_id=file_id,
                source_type="gdrive",
                source_url=gdrive_url,
                extra_metadata=metadata,
            )
        except AgentFailureError as exc:
            return exc.failure


def _build_parser_output(
    chunks: list[ParsedChunk],
    metadata: dict[str, Any],
) -> ParserOutput:
    document_id = metadata.get("document_id") or str(uuid.uuid4())
    page_numbers = [chunk.page_number for chunk in chunks if chunk.page_number]
    total_pages = max(page_numbers) if page_numbers else max(1, len(chunks))
    return ParserOutput(
        document_id=document_id,
        metadata=dict(metadata),
        chunks=chunks,
        total_pages=total_pages,
        processing_time_ms=0.0,
    )


__all__ = ["IngestionService"]
