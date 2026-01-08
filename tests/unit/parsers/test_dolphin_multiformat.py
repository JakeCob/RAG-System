"""Unit tests for multi-format parsing."""

from pathlib import Path

import pytest

from app.schemas import AgentFailure, ErrorCodes
from app.schemas.parser import ParsedChunk
from ingestion.dolphin import DolphinParser


FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "documents"
PDF_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "AI Engineering Building Applications with Foundation Models "
    "(Chip Huyen) (Z-Library).pdf"
)


class TestDolphinParser:
    """Test suite for multi-format document parsing."""

    @pytest.mark.unit
    def test_parse_txt_file(self) -> None:
        """Test plain text parsing."""
        parser = DolphinParser()
        with open(FIXTURES_DIR / "sample.txt", "rb") as handle:
            content = handle.read()

        result = parser.parse(content, metadata={"filename": "sample.txt"})

        assert isinstance(result, list)
        assert all(isinstance(chunk, ParsedChunk) for chunk in result)
        assert result[0].layout_type == "text"

    @pytest.mark.unit
    def test_parse_markdown_with_table(self) -> None:
        """Test markdown parsing preserves tables."""
        parser = DolphinParser()
        with open(FIXTURES_DIR / "sample.md", "rb") as handle:
            content = handle.read()

        result = parser.parse(content, metadata={"filename": "sample.md"})

        assert isinstance(result, list)
        table_chunks = [chunk for chunk in result if chunk.layout_type == "table"]
        assert len(table_chunks) > 0

    @pytest.mark.unit
    def test_parse_pdf_with_tables(self) -> None:
        """Test PDF parsing with table detection."""
        parser = DolphinParser()
        if not PDF_FIXTURE.exists():
            pytest.skip(f"Missing PDF fixture at {PDF_FIXTURE}")
        with open(PDF_FIXTURE, "rb") as handle:
            content = handle.read()

        result = parser.parse(content, metadata={"filename": PDF_FIXTURE.name})

        assert isinstance(result, list)
        assert len(result) > 0

        table_chunks = [chunk for chunk in result if chunk.layout_type == "table"]
        assert len(table_chunks) > 0, "PDF should contain at least one table"

        page_numbered = [chunk for chunk in result if chunk.page_number is not None]
        assert len(page_numbered) > 0, "Expected at least some page numbers"

    @pytest.mark.unit
    def test_parse_docx_headers_and_lists(self) -> None:
        """Test DOCX parsing preserves structure."""
        parser = DolphinParser()
        with open(FIXTURES_DIR / "sample.docx", "rb") as handle:
            content = handle.read()

        result = parser.parse(content, metadata={"filename": "sample.docx"})

        assert isinstance(result, list)
        assert len(result) > 0

        header_chunks = [chunk for chunk in result if chunk.layout_type == "header"]
        assert len(header_chunks) > 0

    @pytest.mark.unit
    def test_parse_docx_tables(self) -> None:
        """Test DOCX parsing extracts tables."""
        parser = DolphinParser()
        with open(FIXTURES_DIR / "sample.docx", "rb") as handle:
            content = handle.read()

        result = parser.parse(content, metadata={"filename": "sample.docx"})

        table_chunks = [chunk for chunk in result if chunk.layout_type == "table"]
        assert len(table_chunks) > 0

    @pytest.mark.unit
    def test_parse_pptx_slides_and_notes(self) -> None:
        """Test PowerPoint parsing extracts slides."""
        parser = DolphinParser()
        with open(FIXTURES_DIR / "sample.pptx", "rb") as handle:
            content = handle.read()

        result = parser.parse(content, metadata={"filename": "sample.pptx"})

        assert isinstance(result, list)
        assert len(result) >= 3, "Should have at least 3 slides"
        page_numbered = [chunk for chunk in result if chunk.page_number is not None]
        assert len(page_numbered) >= 2, "Most slides should have page numbers"

    @pytest.mark.unit
    def test_parse_xlsx_to_markdown_table(self) -> None:
        """Test Excel parsing converts to markdown tables."""
        parser = DolphinParser()
        with open(FIXTURES_DIR / "sample.xlsx", "rb") as handle:
            content = handle.read()

        result = parser.parse(content, metadata={"filename": "sample.xlsx"})

        assert isinstance(result, list)
        assert len(result) >= 2, "Should have 2 sheets"
        assert all(chunk.layout_type == "table" for chunk in result)
        assert all("|" in chunk.content for chunk in result)

    @pytest.mark.unit
    def test_parse_csv_file(self) -> None:
        """Test CSV parsing."""
        parser = DolphinParser()
        with open(FIXTURES_DIR / "sample.csv", "rb") as handle:
            content = handle.read()

        result = parser.parse(content, metadata={"filename": "sample.csv"})

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].layout_type == "table"
        assert "|" in result[0].content

    @pytest.mark.unit
    def test_parse_malformed_pdf(self) -> None:
        """Test error handling for corrupted files."""
        parser = DolphinParser()
        with open(FIXTURES_DIR / "corrupted.pdf", "rb") as handle:
            content = handle.read()

        result = parser.parse(content, metadata={"filename": "corrupted.pdf"})

        assert isinstance(result, AgentFailure)
        assert result.error_code in {
            ErrorCodes.PARSER_INVALID_INPUT,
            ErrorCodes.PARSER_CORRUPTED_FILE,
        }

    @pytest.mark.unit
    def test_parse_unsupported_format(self) -> None:
        """Test error for unsupported file types."""
        parser = DolphinParser()
        result = parser.parse(b"fake content", metadata={"filename": "file.xyz"})

        assert isinstance(result, AgentFailure)
        assert result.error_code == ErrorCodes.PARSER_UNSUPPORTED_FORMAT
        assert ".xyz" in result.message

    @pytest.mark.unit
    def test_reject_html_file(self) -> None:
        """Test HTML files are rejected in favor of the Web Connector."""
        parser = DolphinParser()
        result = parser.parse(b"<html></html>", metadata={"filename": "page.html"})

        assert isinstance(result, AgentFailure)
        assert result.error_code == ErrorCodes.PARSER_UNSUPPORTED_FORMAT
        assert "Web Connector" in result.message

    @pytest.mark.unit
    def test_parse_scanned_pdf_with_ocr(self) -> None:
        """Test OCR on scanned PDFs."""
        parser = DolphinParser(enable_ocr=True)
        with open(FIXTURES_DIR / "scanned.pdf", "rb") as handle:
            content = handle.read()

        result = parser.parse(content, metadata={"filename": "scanned.pdf"})

        if isinstance(result, AgentFailure):
            assert result.error_code == ErrorCodes.PARSER_OCR_FAILED
        else:
            assert isinstance(result, list)
            assert len(result) > 0
