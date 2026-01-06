"""Memory Agent tests.

Reference: docs/04_TEST_PLAN.md Section 3.3
Test Class: TestMemoryAgent
"""

import tempfile
from typing import Any

import pytest

from app.memory.agent import MemoryAgent
from app.schemas import AgentFailure, ErrorCodes, MemoryQuery
from app.schemas.parser import ParsedChunk


# =============================================================================
# Mock Embedding Generator for Unit Tests
# =============================================================================


class MockEmbeddingGenerator:
    """Mock embedding generator for fast unit tests without loading models."""

    def __init__(self, model_name: str = "mock-model") -> None:
        self.model_name = model_name
        self.embedding_dim = 384  # Match real model dimension

    def embed_text(self, text: str) -> list[float]:
        """Generate deterministic mock embedding based on text length."""
        # Simple hash-based mock: use text length and hash
        base_value = float(len(text)) / 1000.0
        return [base_value + (i * 0.001) for i in range(self.embedding_dim)]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        return [self.embed_text(text) for text in texts]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_db_path() -> Any:
    """Provide a temporary directory for LanceDB testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_embedding_gen() -> MockEmbeddingGenerator:
    """Provide a mock embedding generator for tests."""
    return MockEmbeddingGenerator()


@pytest.fixture
def memory_agent(temp_db_path: str, mock_embedding_gen: MockEmbeddingGenerator) -> Any:
    """Provide a MemoryAgent with mocked embeddings for testing."""
    agent = MemoryAgent(db_path=temp_db_path)
    # Replace with mock for faster tests
    agent.embedding_generator = mock_embedding_gen
    return agent


@pytest.fixture
def sample_chunks() -> list[ParsedChunk]:
    """Provide sample parsed chunks for testing."""
    return [
        ParsedChunk(
            chunk_id="chunk_001",
            content="Python is a programming language used for web development.",
            chunk_index=0,
            layout_type="text",
            page_number=1,
        ),
        ParsedChunk(
            chunk_id="chunk_002",
            content="FastAPI is a modern web framework for building APIs with Python.",
            chunk_index=1,
            layout_type="text",
            page_number=1,
        ),
        ParsedChunk(
            chunk_id="chunk_003",
            content="LanceDB is a vector database optimized for AI applications.",
            chunk_index=2,
            layout_type="text",
            page_number=2,
        ),
    ]


@pytest.fixture
def gdrive_metadata() -> dict[str, Any]:
    """Provide sample GDrive source metadata."""
    return {
        "source_id": "gdrive_doc_123",
        "source_type": "gdrive",
        "url": "https://drive.google.com/file/d/123/view",
        "title": "Technical Documentation",
        "author": "user@example.com",
    }


# =============================================================================
# Test Cases
# =============================================================================


class TestMemoryAgent:
    """Tests for the Memory Agent ("The Librarian")."""

    @pytest.mark.unit
    async def test_add_documents(
        self,
        memory_agent: MemoryAgent,
        sample_chunks: list[ParsedChunk],
        gdrive_metadata: dict[str, Any],
    ) -> None:
        """Add documents with embeddings to LanceDB.

        Verifies:
        - Documents are stored successfully
        - Chunk IDs are returned
        - No errors occur during storage
        """
        # Act
        chunk_ids = await memory_agent.add_documents(
            chunks=sample_chunks,
            source_metadata=gdrive_metadata,
        )

        # Assert
        assert len(chunk_ids) == 3
        assert chunk_ids == ["chunk_001", "chunk_002", "chunk_003"]

    @pytest.mark.unit
    async def test_retrieve_no_results(
        self,
        memory_agent: MemoryAgent,
    ) -> None:
        """Query with no matches returns AgentFailure ERR_MEMORY_NO_RESULTS.

        Scenario: Empty database, query for "Zorglub's exploits"
        Expected: AgentFailure with MEMORY_NO_RESULTS error code
        """
        # Arrange
        query = MemoryQuery(
            query_text="Zorglub's exploits in the multiverse",
            top_k=5,
            min_relevance_score=0.7,
        )

        # Act
        result = await memory_agent.query(query)

        # Assert
        assert isinstance(result, AgentFailure)
        assert result.error_code == ErrorCodes.MEMORY_NO_RESULTS
        assert result.recoverable is True

    @pytest.mark.unit
    async def test_exact_match_retrieval(
        self,
        memory_agent: MemoryAgent,
        gdrive_metadata: dict[str, Any],
    ) -> None:
        """Known text retrieved with score > 0.9.

        Scenario: Seed DB with "The code is 1234", query "What is the code?"
        Expected: Top result has high relevance score (> 0.9) and matches text
        """
        # Arrange - Add a specific document
        secret_chunk = ParsedChunk(
            chunk_id="secret_001",
            content="The secret code is 1234. Use it to access the vault.",
            chunk_index=0,
            layout_type="text",
        )
        await memory_agent.add_documents(
            chunks=[secret_chunk],
            source_metadata={**gdrive_metadata, "source_id": "secret_doc"},
        )

        # Act - Query for similar content
        query = MemoryQuery(
            query_text="What is the secret code?",
            top_k=5,
            min_relevance_score=0.7,
        )
        result = await memory_agent.query(query)

        # Assert
        assert not isinstance(result, AgentFailure)
        assert result.total_found > 0
        assert len(result.results) > 0

        # Check top result has high score
        top_result = result.results[0]
        assert top_result.relevance_score >= 0.9
        assert "1234" in top_result.content
        assert top_result.chunk_id == "secret_001"

    @pytest.mark.unit
    async def test_metadata_filtering(
        self,
        memory_agent: MemoryAgent,
        sample_chunks: list[ParsedChunk],
    ) -> None:
        """Filter by source_type returns only matching chunks.

        Scenario:
        - Add docs from gdrive (source_type="gdrive")
        - Add docs from local (source_type="local")
        - Query with filter={"source_type": "gdrive"}
        Expected: Only gdrive chunks are returned
        """
        # Arrange - Add GDrive documents
        gdrive_meta = {
            "source_id": "gdrive_doc_1",
            "source_type": "gdrive",
            "url": "https://drive.google.com/123",
        }
        await memory_agent.add_documents(
            chunks=sample_chunks[:2],  # First 2 chunks
            source_metadata=gdrive_meta,
        )

        # Add local documents
        local_meta = {
            "source_id": "local_doc_1",
            "source_type": "local",
            "url": None,
        }
        await memory_agent.add_documents(
            chunks=sample_chunks[2:],  # Last chunk
            source_metadata=local_meta,
        )

        # Act - Query with gdrive filter
        query = MemoryQuery(
            query_text="Python programming",
            top_k=10,
            min_relevance_score=0.5,
            filters={"source_type": "gdrive"},
        )
        result = await memory_agent.query(query)

        # Assert
        assert not isinstance(result, AgentFailure)
        assert result.total_found > 0

        # All results should be from gdrive
        for ctx in result.results:
            assert ctx.metadata["source_type"] == "gdrive"
            assert ctx.source_id == "gdrive_doc_1"

    @pytest.mark.unit
    async def test_relevance_score_threshold(
        self,
        memory_agent: MemoryAgent,
        sample_chunks: list[ParsedChunk],
        gdrive_metadata: dict[str, Any],
    ) -> None:
        """Results below min_relevance_score are filtered out.

        Scenario:
        - Add documents about Python and databases
        - Query with high threshold (0.95)
        Expected: Only very relevant results returned or AgentFailure
        """
        # Arrange
        await memory_agent.add_documents(
            chunks=sample_chunks,
            source_metadata=gdrive_metadata,
        )

        # Act - Query with very high threshold
        query = MemoryQuery(
            query_text="Quantum physics and relativity",  # Unrelated topic
            top_k=5,
            min_relevance_score=0.95,  # Very high threshold
        )
        result = await memory_agent.query(query)

        # Assert - Should return failure or empty results
        if isinstance(result, AgentFailure):
            assert result.error_code == ErrorCodes.MEMORY_NO_RESULTS
        else:
            # If any results, they must meet the threshold
            for ctx in result.results:
                assert ctx.relevance_score >= 0.95

    @pytest.mark.unit
    async def test_delete_by_source(
        self,
        memory_agent: MemoryAgent,
        sample_chunks: list[ParsedChunk],
        gdrive_metadata: dict[str, Any],
    ) -> None:
        """Delete all chunks from a source.

        Verifies:
        - Chunks are deleted successfully
        - Count of deleted chunks is returned
        - Subsequent queries don't return deleted chunks
        """
        # Arrange - Add documents
        await memory_agent.add_documents(
            chunks=sample_chunks,
            source_metadata=gdrive_metadata,
        )

        # Act - Delete by source
        deleted_count = await memory_agent.delete_by_source(
            source_id=gdrive_metadata["source_id"]
        )

        # Assert
        assert deleted_count == 3  # All 3 chunks deleted

        # Verify they're gone
        query = MemoryQuery(
            query_text="Python programming",
            top_k=10,
            min_relevance_score=0.5,
        )
        result = await memory_agent.query(query)

        # Should get no results
        assert isinstance(result, AgentFailure)
        assert result.error_code == ErrorCodes.MEMORY_NO_RESULTS


# =============================================================================
# Integration-style Tests (with real embeddings)
# =============================================================================


class TestMemoryAgentWithRealEmbeddings:
    """Tests using actual sentence-transformers (slower, more realistic)."""

    @pytest.mark.integration
    async def test_semantic_similarity_search(self, temp_db_path: str) -> None:
        """Test semantic search with real embeddings.

        This test uses actual sentence-transformers to verify
        that semantically similar queries return relevant results.
        """
        # Arrange
        agent = MemoryAgent(db_path=temp_db_path)

        chunks = [
            ParsedChunk(
                chunk_id="chunk_001",
                content="Machine learning is a subset of artificial intelligence.",
                chunk_index=0,
                layout_type="text",
            ),
            ParsedChunk(
                chunk_id="chunk_002",
                content="Deep learning uses neural networks with multiple layers.",
                chunk_index=1,
                layout_type="text",
            ),
            ParsedChunk(
                chunk_id="chunk_003",
                content="The recipe calls for 2 cups of flour and 1 cup of sugar.",
                chunk_index=2,
                layout_type="text",
            ),
        ]

        await agent.add_documents(
            chunks=chunks,
            source_metadata={"source_id": "test_doc", "source_type": "local"},
        )

        # Act - Query for AI-related content
        query = MemoryQuery(
            query_text="Tell me about neural networks and AI",
            top_k=3,
            min_relevance_score=0.3,
        )
        result = await agent.query(query)

        # Assert
        assert not isinstance(result, AgentFailure)
        assert result.total_found > 0

        # The cooking recipe should have lower relevance than AI chunks
        # (This is a semantic understanding test)
        ai_chunks = [r for r in result.results if r.chunk_id != "chunk_003"]
        cooking_chunks = [r for r in result.results if r.chunk_id == "chunk_003"]

        if ai_chunks and cooking_chunks:
            assert ai_chunks[0].relevance_score > cooking_chunks[0].relevance_score
