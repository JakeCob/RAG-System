import uuid
from typing import Any

from app.schemas.parser import ParsedChunk


class BaseParser:
    """Base class for all ingestion parsers."""

    def _decode_content(self, content: str | bytes) -> str:
        """Decode raw content into a string.

        Args:
            content: Raw content as `str` or `bytes`.

        Returns:
            Decoded string content.
        """
        if isinstance(content, bytes):
            # Simple decode for bytes, assuming utf-8 for this skeleton
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content.decode("latin-1")
        return content

    def parse(
        self, content: str | bytes, metadata: dict[str, Any]
    ) -> list[ParsedChunk]:
        """Parse raw content into structured chunks.

        Args:
            content: Raw file content (str or bytes).
            metadata: Metadata associated with the content (e.g., URL, title).

        Returns:
            A list of structured chunks.
        """
        if not isinstance(metadata, dict):
            raise TypeError("metadata must be a dict.")
        text = self._decode_content(content)

        if not text:
            raise ValueError("Content cannot be empty.")

        chunks_text = self.chunk(text)
        parsed_chunks = []

        for i, chunk_text in enumerate(chunks_text):
            parsed_chunks.append(
                ParsedChunk(
                    chunk_id=str(uuid.uuid4()),
                    content=chunk_text,
                    chunk_index=i,
                    layout_type="text",
                    bbox=None,
                )
            )
        return parsed_chunks

    def chunk(self, text: str, limit: int = 1000) -> list[str]:
        """Split text into smaller chunks based on a character limit.

        Args:
            text: The text to split.
            limit: Maximum characters per chunk.

        Returns:
            A list of text chunks.
        """
        return [text[i : i + limit] for i in range(0, len(text), limit)]
