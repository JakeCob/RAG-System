"""Mock Vector Database for testing.

Provides in-memory vector storage for testing the Memory Agent
without requiring LanceDB dependencies.

Reference: docs/04_TEST_PLAN.md Section 2.3
"""

from typing import Any

from app.schemas import MemoryOutput, MemoryQuery, RetrievedContext


class MockLanceDB:
    """In-memory mock LanceDB for testing.

    Mimics the LanceDB interface used by the Memory Agent.
    Uses ephemeral storage for test isolation.
    """

    def __init__(self) -> None:
        """Initialize empty document store."""
        self.documents: list[dict[str, Any]] = []
        self.embeddings: list[list[float]] = []
        self._call_history: list[dict[str, Any]] = []

    async def add_documents(
        self,
        documents: list[str],
        embeddings: list[list[float]],
        metadata: list[dict[str, Any]] | None = None,
        source_ids: list[str] | None = None,
    ) -> list[str]:
        """Add documents with their embeddings (LanceDB-style).

        Args:
            documents: List of document texts.
            embeddings: List of embedding vectors.
            metadata: Optional metadata for each document.
            source_ids: Optional source identifiers.

        Returns:
            List of generated chunk IDs.
        """
        self._call_history.append(
            {
                "method": "add_documents",
                "count": len(documents),
            }
        )

        ids: list[str] = []
        for i, (doc, emb) in enumerate(zip(documents, embeddings, strict=True)):
            chunk_id = f"chunk_{len(self.documents) + i}"
            source_id = source_ids[i] if source_ids else f"source_{i}"
            self.documents.append(
                {
                    "chunk_id": chunk_id,
                    "content": doc,
                    "source_id": source_id,
                    "metadata": metadata[i] if metadata else {},
                }
            )
            self.embeddings.append(emb)
            ids.append(chunk_id)
        return ids

    async def query(
        self,
        query: MemoryQuery,
    ) -> MemoryOutput:
        """Query for similar documents using MemoryQuery schema.

        Args:
            query: The memory query with filters and parameters.

        Returns:
            MemoryOutput with retrieved contexts.
        """
        self._call_history.append(
            {
                "method": "query",
                "query_text": query.query_text,
                "top_k": query.top_k,
            }
        )

        # Apply metadata filters if present
        filtered_docs = self.documents
        if query.filters:
            filtered_docs = [
                doc
                for doc in self.documents
                if all(
                    doc.get("metadata", {}).get(k) == v
                    for k, v in query.filters.items()
                )
            ]

        # Return top_k results with mock scores
        results: list[RetrievedContext] = []
        for i, doc in enumerate(filtered_docs[: query.top_k]):
            score = 0.95 - (i * 0.05)  # Decreasing mock scores
            if score >= query.min_relevance_score:
                results.append(
                    RetrievedContext(
                        chunk_id=doc["chunk_id"],
                        content=doc["content"],
                        source_id=doc["source_id"],
                        source_url=doc.get("metadata", {}).get("url"),
                        relevance_score=score,
                        metadata=doc.get("metadata", {}),
                    )
                )

        return MemoryOutput(results=results, total_found=len(results))

    def reset(self) -> None:
        """Clear all stored documents and call history."""
        self.documents = []
        self.embeddings = []
        self._call_history = []

    @property
    def call_history(self) -> list[dict[str, Any]]:
        """Get the history of method calls for assertions."""
        return self._call_history


# Backward compatibility alias
MockVectorDB = MockLanceDB
