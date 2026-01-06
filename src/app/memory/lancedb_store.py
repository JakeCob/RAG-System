"""LanceDB wrapper for vector storage.

Provides an async interface to LanceDB for storing and retrieving
document embeddings with metadata.

Reference: docs/01_DESIGN_DOC.md (LanceDB as vector store)
"""

from typing import Any

import lancedb
import pyarrow as pa  # type: ignore[import-untyped]

from app.schemas import AgentFailure, ErrorCodes, MemoryOutput, RetrievedContext


class LanceDBStore:
    """LanceDB wrapper for vector storage operations.

    Schema:
        - chunk_id: str (unique identifier)
        - content: str (text content)
        - embedding: list[float] (vector)
        - source_id: str (document identifier)
        - source_url: str | None (optional URL)
        - metadata: dict (additional metadata)
    """

    def __init__(self, db_path: str, embedding_dim: int = 384) -> None:
        """Initialize LanceDB connection.

        Args:
            db_path: Path to the LanceDB database directory.
            embedding_dim: Dimension of the embedding vectors (default 384).
        """
        self.db_path = db_path
        self.embedding_dim = embedding_dim
        self.db = lancedb.connect(db_path)
        self.table_name = "documents"

    def _get_schema(self) -> pa.Schema:
        """Define the PyArrow schema for the LanceDB table."""
        return pa.schema(
            [
                pa.field("chunk_id", pa.string()),
                pa.field("content", pa.string()),
                pa.field(
                    "embedding",
                    pa.list_(pa.float32(), list_size=self.embedding_dim),
                ),
                pa.field("source_id", pa.string()),
                pa.field("source_url", pa.string()),
                pa.field("metadata", pa.string()),  # JSON-encoded
            ]
        )

    async def add_documents(
        self,
        chunk_ids: list[str],
        contents: list[str],
        embeddings: list[list[float]],
        source_ids: list[str],
        source_urls: list[str | None],
        metadata_list: list[dict[str, Any]],
    ) -> None:
        """Add documents with embeddings to LanceDB.

        Args:
            chunk_ids: List of unique chunk identifiers.
            contents: List of text contents.
            embeddings: List of embedding vectors.
            source_ids: List of source document identifiers.
            source_urls: List of source URLs (can be None).
            metadata_list: List of metadata dictionaries.
        """
        import json

        # Prepare data for insertion
        data = []
        for chunk_id, content, emb, src_id, src_url, meta in zip(
            chunk_ids,
            contents,
            embeddings,
            source_ids,
            source_urls,
            metadata_list,
            strict=True,
        ):
            data.append(
                {
                    "chunk_id": chunk_id,
                    "content": content,
                    "embedding": emb,
                    "source_id": src_id,
                    "source_url": src_url if src_url else "",
                    "metadata": json.dumps(meta),
                }
            )

        # Create or append to table
        try:
            table = self.db.open_table(self.table_name)
            table.add(data)
        except (FileNotFoundError, ValueError):
            # Table doesn't exist, create it
            self.db.create_table(self.table_name, data=data, mode="overwrite")

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        min_score: float = 0.7,
        filters: dict[str, Any] | None = None,
    ) -> MemoryOutput | AgentFailure:
        """Search for similar documents using vector similarity.

        Args:
            query_embedding: The query embedding vector.
            top_k: Maximum number of results to return.
            min_score: Minimum relevance score threshold.
            filters: Optional metadata filters.

        Returns:
            MemoryOutput with results or AgentFailure if no results.
        """
        import json

        try:
            table = self.db.open_table(self.table_name)
        except (FileNotFoundError, ValueError):
            return AgentFailure(
                agent_id="memory",
                error_code=ErrorCodes.MEMORY_NO_RESULTS,
                message="No documents in vector store",
                recoverable=True,
            )

        # Perform vector search
        results = (
            table.search(query_embedding)
            .metric("cosine")
            .limit(top_k * 2)  # Get more results to allow filtering
            .to_list()
        )

        # Filter and convert results
        retrieved_contexts: list[RetrievedContext] = []
        for result in results:
            # LanceDB returns cosine similarity (0-2 range, higher is more similar)
            # Convert to 0-1 scale where 1 is perfect match
            cosine_similarity = result.get("_distance", 0.0)
            relevance_score = 1.0 - (cosine_similarity / 2.0)

            # Apply min_score filter
            if relevance_score < min_score:
                continue

            # Parse metadata
            metadata = json.loads(result["metadata"])

            # Apply metadata filters if present
            if filters and not all(
                metadata.get(k) == v for k, v in filters.items()
            ):
                continue

            # Only add if we haven't reached top_k yet
            if len(retrieved_contexts) >= top_k:
                break

            retrieved_contexts.append(
                RetrievedContext(
                    chunk_id=result["chunk_id"],
                    content=result["content"],
                    source_id=result["source_id"],
                    source_url=result["source_url"] if result["source_url"] else None,
                    relevance_score=float(relevance_score),
                    metadata=metadata,
                )
            )

        if not retrieved_contexts:
            return AgentFailure(
                agent_id="memory",
                error_code=ErrorCodes.MEMORY_NO_RESULTS,
                message=f"No results above threshold {min_score}",
                recoverable=True,
                details={"min_score": min_score, "filters": filters},
            )

        return MemoryOutput(
            results=retrieved_contexts,
            total_found=len(retrieved_contexts),
        )

    async def delete_by_source(self, source_id: str) -> int:
        """Delete all chunks from a specific source.

        Args:
            source_id: The source document identifier.

        Returns:
            Number of chunks deleted.
        """
        try:
            table = self.db.open_table(self.table_name)
            # Count matching records before deletion
            all_records = table.to_pandas()
            count = len(all_records[all_records["source_id"] == source_id])

            # Delete matching records
            table.delete(f'source_id = "{source_id}"')
            return count
        except (FileNotFoundError, ValueError):
            return 0
