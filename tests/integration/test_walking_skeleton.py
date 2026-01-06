
import pytest
from src.brain.engine import RAGEngine
from src.ingestion.base import BaseParser


@pytest.mark.asyncio
async def test_walking_skeleton(mock_web_content, mock_llm):
    """
    P1-5: The "Walking Skeleton" (Integration Test)

    Verifies the end-to-end flow: Ingest -> Index -> Retrieve -> Answer.
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
    # Step 2: Simulate Indexing (Manual)
    # =========================================================================
    # We create an in-memory vector store that adheres to the interface expected by RAGEngine
    # (specifically, an async search method returning a list of dicts).

    class InMemoryVectorStore:
        def __init__(self, chunks, metadata):
            self.chunks = chunks
            self.metadata = metadata

        async def search(self, query: str):
            # For this skeleton, we simply return all chunks as matches.
            # In a real system, this would do similarity search.
            results = []
            for c in self.chunks:
                results.append({
                    "id": c.chunk_id,
                    "content": c.content,
                    "score": 1.0,  # Simulate perfect match
                    "metadata": self.metadata  # Pass the source metadata
                })
            return results

    vector_store = InMemoryVectorStore(chunks, metadata)

    # =========================================================================
    # Step 3: Retrieve
    # =========================================================================
    engine = RAGEngine(vector_store=vector_store, llm_client=mock_llm)

    query = "What is the summary?"
    context_nodes = await engine.retrieve(query)

    # Assertions for Step 3
    assert len(context_nodes) > 0, "Retrieve should return context nodes"
    assert context_nodes[0].text == chunks[0].content, "Retrieved content should match ingested content"
    assert context_nodes[0].metadata["url"] == source_url, "Metadata should be preserved"

    # =========================================================================
    # Step 4: Answer
    # =========================================================================
    # Configure mock LLM response
    mock_llm.responses["What is the summary?"] = "This is a summary of the government notice."

    answer = await engine.generate_answer(query, context_nodes)

    # Critical Assertions for Step 4
    assert answer.content == "This is a summary of the government notice."

    # Assert that the final Answer object contains a citation that traces back to the original URL
    assert len(answer.citations) > 0, "Answer should contain citations"
    assert answer.citations[0].source_id == source_url, "Citation source_id should match original URL"
