"""Walking Skeleton Integration Test with LanceDB.

This test verifies end-to-end flow with real LanceDB integration:
Ingest -> Index -> Retrieve -> Answer

Reference: docs/04_TEST_PLAN.md Section 5
"""

import tempfile

import pytest
from src.brain.engine import RAGEngine
from src.ingestion.base import BaseParser

from app.memory.agent import MemoryAgent


@pytest.mark.integration
async def test_walking_skeleton_with_lancedb(
    mock_web_content: dict[str, str],
    mock_llm: any,
) -> None:
    """P2-3: Walking Skeleton with LanceDB.

    Verifies the end-to-end flow with real LanceDB storage:
    1. Parse content into chunks
    2. Store chunks with embeddings in LanceDB
    3. Retrieve relevant chunks via semantic search
    4. Generate answer with citations
    """
    # =========================================================================
    # Step 1: Ingest
    # =========================================================================
    parser = BaseParser()
    content = mock_web_content["markdown"]
    source_url = "https://gov.local/notice/123"
    metadata = {"url": source_url, "title": "Test Doc"}

    chunks = parser.parse(content, metadata)

    # Assertions for Step 1
    assert len(chunks) > 0, "Parser should produce at least one chunk"
    assert chunks[0].content, "Chunk content should not be empty"

    # =========================================================================
    # Step 2: Index with LanceDB
    # =========================================================================
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize Memory Agent with temporary LanceDB
        memory_agent = MemoryAgent(db_path=tmpdir)

        # Store chunks with embeddings
        chunk_ids = await memory_agent.add_documents(
            chunks=chunks,
            source_metadata={
                "source_id": source_url,
                "url": source_url,
                "title": "Test Doc",
            },
        )

        assert len(chunk_ids) == len(chunks), "All chunks should be stored"

        # =====================================================================
        # Step 3: Retrieve via Memory Agent
        # =====================================================================
        from app.schemas import MemoryQuery

        query_text = "What is the summary?"
        memory_query = MemoryQuery(
            query_text=query_text,
            top_k=5,
            min_relevance_score=0.3,  # Lower threshold for integration test
        )

        memory_result = await memory_agent.query(memory_query)

        # Assertions for Step 3
        assert not isinstance(memory_result, Exception)
        assert memory_result.total_found > 0, "Should retrieve context nodes"
        assert len(memory_result.results) > 0

        # Verify metadata is preserved
        first_result = memory_result.results[0]
        assert first_result.source_id == source_url
        assert first_result.source_url == source_url

        # =====================================================================
        # Step 4: Generate Answer with RAGEngine
        # =====================================================================
        # Create a simple adapter for RAGEngine
        class MemoryAgentAdapter:
            """Adapter to make MemoryAgent compatible with RAGEngine."""

            def __init__(self, agent: MemoryAgent) -> None:
                self.agent = agent

            async def search(self, query: str) -> list[dict[str, any]]:
                """Search method compatible with RAGEngine."""
                memory_query = MemoryQuery(
                    query_text=query,
                    top_k=5,
                    min_relevance_score=0.3,
                )
                result = await self.agent.query(memory_query)

                if isinstance(result, Exception):
                    return []

                # Convert to RAGEngine format
                return [
                    {
                        "id": ctx.chunk_id,
                        "content": ctx.content,
                        "score": ctx.relevance_score,
                        "metadata": {
                            "url": ctx.source_url,
                            "source_id": ctx.source_id,
                            **ctx.metadata,
                        },
                    }
                    for ctx in result.results
                ]

        # Create RAGEngine with LanceDB-backed memory
        vector_store = MemoryAgentAdapter(memory_agent)
        engine = RAGEngine(vector_store=vector_store, llm_client=mock_llm)

        # Configure mock LLM response
        mock_llm.responses[query_text] = (
            "This is a summary of the government notice."
        )

        # Retrieve context
        context_nodes = await engine.retrieve(query_text)
        assert len(context_nodes) > 0, "Should retrieve context via adapter"

        # Generate answer
        answer = await engine.generate_answer(query_text, context_nodes)

        # Critical Assertions for Step 4
        assert answer.content == "This is a summary of the government notice."

        # Assert that citations trace back to original URL
        assert len(answer.citations) > 0, "Answer should contain citations"
        assert (
            answer.citations[0].source_id == source_url
        ), "Citation source_id should match original URL"
