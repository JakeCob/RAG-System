"""Integration test: Upload multi-format docs → query → retrieval."""

from pathlib import Path

import pytest

from app.ingestion.service import IngestionService
from app.memory.agent import MemoryAgent
from app.schemas import MemoryQuery
from ingestion.dolphin import DolphinParser


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "documents"
PDF_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "AI Engineering Building Applications with Foundation Models "
    "(Chip Huyen) (Z-Library).pdf"
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_pdf_and_query(tmp_path) -> None:
    """Test PDF ingestion → semantic search."""
    memory = MemoryAgent(db_path=str(tmp_path / "test.lance"))
    parser = DolphinParser()
    service = IngestionService(memory_agent=memory, parser=parser)

    if not PDF_FIXTURE.exists():
        pytest.skip(f"Missing PDF fixture at {PDF_FIXTURE}")
    with open(PDF_FIXTURE, "rb") as handle:
        content = handle.read()

    parser_output = await service.ingest_document(
        content=content,
        filename=PDF_FIXTURE.name,
        source_type="local",
    )

    assert parser_output.total_pages > 0
    assert len(parser_output.chunks) > 0

    query = MemoryQuery(query_text="What is AI Engineering about?", top_k=5)
    result = await memory.query(query)

    assert result.total_found > 0
    assert any(
        "ai engineering" in ctx.content.lower()
        or "foundation models" in ctx.content.lower()
        for ctx in result.results
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_docx_with_tables(tmp_path) -> None:
    """Test DOCX ingestion with table preservation."""
    memory = MemoryAgent(db_path=str(tmp_path / "test.lance"))
    parser = DolphinParser()
    service = IngestionService(memory_agent=memory, parser=parser)

    with open(FIXTURES_DIR / "sample.docx", "rb") as handle:
        content = handle.read()

    parser_output = await service.ingest_document(
        content=content,
        filename="sample.docx",
        source_type="local",
    )

    table_chunks = [
        chunk for chunk in parser_output.chunks if chunk.layout_type == "table"
    ]
    assert len(table_chunks) > 0, "DOCX should have table chunks"
