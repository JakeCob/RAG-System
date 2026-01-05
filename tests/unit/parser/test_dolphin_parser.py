"""Dolphin Parser Agent tests.

Reference: docs/04_TEST_PLAN.md Section 3.1
Test Class: TestDolphinParser
"""

import pytest


class TestDolphinParser:
    """Tests for the Dolphin Parser Agent ("The Eyes")."""

    @pytest.mark.unit
    def test_parse_malformed_pdf(self) -> None:
        """Input a corrupted PDF byte stream.

        Expect AgentFailure (recoverable=False).
        """
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_parse_empty_string(self) -> None:
        """Input empty text file.

        Expect explicit warning or empty chunk list, not a crash.
        """
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_parse_table_structure(self) -> None:
        """Input Markdown with a table.

        Assert output ParsedChunk preserves pipe | separators
        and is layout_type="table".
        """
        pytest.skip("Not implemented - P1-2")

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
