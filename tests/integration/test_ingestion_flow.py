"""Integration test: document upload → ingestion → retrieval.

This test verifies that the fix for P4-1.5 resolves the broken ingestion
pipeline by testing the complete flow from document upload to retrieval.

Reference: P4-1.5 - Fix Document Ingestion Integration
"""

import pytest

from app.ingestion.service import IngestionService
from app.memory.agent import MemoryAgent
from app.schemas import AgentFailure, MemoryQuery


class TestIngestionFlow:
    """Test the complete ingestion pipeline: upload → store → retrieve."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ingest_and_retrieve_document(self, tmp_path) -> None:
        """Test full ingestion pipeline: upload → store → retrieve.

        This test specifically validates the fix for the IngestionService
        calling the correct MemoryAgent.add_documents() method.
        """
        # Setup
        memory = MemoryAgent(db_path=str(tmp_path / "test.lance"))
        service = IngestionService(memory_agent=memory)

        # Ingest a document
        content = "Python is a programming language. It is widely used for AI."
        parser_output = await service.ingest_document(
            content=content,
            filename="test.txt",
            source_id="doc_001",
            source_type="local",
            source_url="file:///test.txt",
        )

        assert len(parser_output.chunks) > 0
        assert parser_output.document_id is not None

        # Query for the ingested content
        query = MemoryQuery(query_text="What is Python?", top_k=3)
        result = await memory.query(query)

        # Verify retrieval works
        assert not isinstance(result, AgentFailure), f"Query failed: {result}"
        assert result.total_found > 0, "No results found after ingestion"
        assert any("Python" in ctx.content for ctx in result.results)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ingest_with_metadata_preservation(self, tmp_path) -> None:
        """Verify that source metadata is preserved during ingestion."""
        # Setup
        memory = MemoryAgent(db_path=str(tmp_path / "test.lance"))
        service = IngestionService(memory_agent=memory)

        # Ingest a document with rich metadata
        content = "LanceDB is a vector database optimized for AI applications."
        parser_output = await service.ingest_document(
            content=content,
            filename="lancedb_intro.md",
            source_id="lancedb_doc_123",
            source_type="gdrive",
            source_url="https://drive.google.com/file/d/abc123",
            extra_metadata={"author": "Jane Doe", "department": "Engineering"},
        )

        assert parser_output.document_id is not None

        # Query and verify metadata is preserved
        query = MemoryQuery(query_text="vector database", top_k=1)
        result = await memory.query(query)

        assert not isinstance(result, AgentFailure)
        assert result.total_found > 0
        assert result.results[0].source_id == "lancedb_doc_123"
        assert result.results[0].source_url == "https://drive.google.com/file/d/abc123"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ingest_multiple_documents(self, tmp_path) -> None:
        """Test ingesting multiple documents and retrieving from them."""
        # Setup
        memory = MemoryAgent(db_path=str(tmp_path / "test.lance"))
        service = IngestionService(memory_agent=memory)

        # Ingest multiple documents
        docs = [
            {
                "content": "FastAPI is a modern Python web framework.",
                "filename": "fastapi.txt",
                "source_id": "doc_fastapi",
            },
            {
                "content": "Pydantic provides data validation for Python.",
                "filename": "pydantic.txt",
                "source_id": "doc_pydantic",
            },
            {
                "content": "LanceDB enables vector search at scale.",
                "filename": "lancedb.txt",
                "source_id": "doc_lancedb",
            },
        ]

        for doc in docs:
            await service.ingest_document(
                content=doc["content"],
                filename=doc["filename"],
                source_id=doc["source_id"],
                source_type="local",
            )

        # Query and verify we can retrieve from multiple documents
        query = MemoryQuery(query_text="Python framework and validation", top_k=5)
        result = await memory.query(query)

        assert not isinstance(result, AgentFailure)
        assert result.total_found >= 1  # Should find at least one document
        source_ids = {ctx.source_id for ctx in result.results}
        assert "doc_fastapi" in source_ids or "doc_pydantic" in source_ids
