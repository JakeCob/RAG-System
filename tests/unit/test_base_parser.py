import pytest

from app.schemas.parser import ParsedChunk
from ingestion.base import BaseParser


class TestBaseParser:
    @pytest.fixture
    def parser(self):
        return BaseParser()

    def test_parse_valid_content(self, parser, mock_crawl_result):
        """
        Test that parse() accepts raw data and returns a List of ParsedChunk objects.

        Requirements:
        1. Accept raw data (string or bytes).
        2. Return List[ParsedChunk] (referencing src.app.schemas.parser.ParsedChunk).
        3. Metadata handling (implied context propagation, though ParsedChunk schema
           doesn't strictly have a 'metadata' field, we verify the structure).
        """
        content = mock_crawl_result.markdown
        metadata = mock_crawl_result.metadata

        # Act
        chunks = parser.parse(content, metadata)

        # Assert
        assert isinstance(chunks, list)
        # Note: Since we are in the Red phase and using 'pass' in implementation,
        # chunks will be None or empty depending on implementation stub.
        # But for TDD, we assert what we EXPECT.

        # We expect a list of ParsedChunk
        assert len(chunks) > 0
        assert isinstance(chunks[0], ParsedChunk)

        # Check that content is preserved in the chunks
        combined_content = "".join([c.content for c in chunks])
        assert len(combined_content) > 0

    def test_chunk_method(self, parser, mock_web_content):
        """
        Test the chunk() method.

        Requirements:
        1. Pass a long string.
        2. Assert it is split into multiple chunks.
        3. Assert no chunk exceeds character limit (1000 chars).
        """
        # Create a long string (> 1000 chars)
        long_text = mock_web_content["markdown"] * 50
        assert len(long_text) > 1000

        chunks = parser.chunk(long_text, limit=1000)

        assert isinstance(chunks, list)
        assert len(chunks) > 1

        for chunk in chunks:
            assert len(chunk) <= 1000

    def test_parse_empty_content_raises_error(self, parser):
        """Test that empty content raises a ValueError."""
        with pytest.raises(ValueError):
            parser.parse("", {"source": "test"})

    def test_parse_bytes_content(self, parser):
        """Test that parse accepts bytes."""
        content = b"Some bytes content"
        metadata = {"source": "bytes"}

        # Should not raise type error
        chunks = parser.parse(content, metadata)
        assert isinstance(chunks, list)
