"""Dolphin Parser Agent tests.

Reference: docs/04_TEST_PLAN.md Section 3.1
Test Class: TestDolphinParser
"""

import pytest

from ingestion.dolphin import DolphinParser


class TestDolphinParser:
    """Tests for the Dolphin Parser Agent ("The Eyes")."""

    @pytest.fixture
    def parser(self):
        return DolphinParser()

    @pytest.mark.unit
    def test_parse_malformed_pdf(self, parser) -> None:
        """Input a corrupted PDF byte stream.

        Expect AgentFailure (recoverable=False).
        """
        _ = parser
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_parse_empty_string(self, parser) -> None:
        """Input empty text file.

        Expect explicit warning or empty chunk list, not a crash.
        """
        # Act
        try:
            result = parser.parse("", metadata={"source": "test"})
            # Depending on implementation, might return empty list or raise
            # BaseParser raises ValueError, let's see if Dolphin overrides or catches
        except ValueError:
            return  # Acceptable behavior

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    def test_parse_table_structure(self, parser) -> None:
        """Input Markdown with a table.

        Assert output ParsedChunk preserves pipe | separators
        and is layout_type="table".
        """
        # Arrange
        markdown_table = """
# Header
| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
"""
        # Act
        chunks = parser.parse(markdown_table, metadata={"source": "test_table"})

        # Assert
        assert len(chunks) > 0
        # Find the chunk containing the table
        table_chunk = next(
            (c for c in chunks if "|" in c.content and "Column 1" in c.content), None
        )
        assert table_chunk is not None
        assert table_chunk.layout_type == "table"

    @pytest.mark.unit
    def test_sanitize_html(self) -> None:
        """Input HTML with <script> tags.

        Assert output text is stripped of scripts.
        """
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_parse_docx_structure(self) -> None:
        """Input a mock DOCX byte stream.

        Assert headers and paragraphs are preserved.
        """
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_parse_pptx_slides(self) -> None:
        """Input a mock PPTX.

        Assert slide titles become headers and speaker notes are extracted.
        """
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_parse_excel_csv(self) -> None:
        """Input a CSV/XLSX.

        Assert rows are converted to Markdown table format.
        """
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_parse_epub_content(self) -> None:
        """Input a mock EPUB.

        Assert chapter titles are preserved as headers
        and text content is extracted cleanly.
        """
        pytest.skip("Not implemented - P1-2")
