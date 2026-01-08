"""Memory Agent implementation - "The Librarian".

Handles document storage, retrieval, and semantic search operations
using LanceDB and sentence-transformers.

Reference: docs/02_AGENT_SPECS.md Section 2.3
"""

from typing import Any

from app.memory.embeddings import EmbeddingGenerator
from app.memory.lancedb_store import LanceDBStore
from app.schemas import AgentFailure, MemoryOutput, MemoryQuery
from app.schemas.parser import ParsedChunk


class MemoryAgent:
    """Memory Agent for semantic search and document storage.

    Responsibilities:
        - Store parsed chunks with embeddings in LanceDB
        - Perform semantic search with relevance filtering
        - Support metadata-based filtering
        - Handle document deletion
    """

    def __init__(
        self,
        db_path: str,
        embedding_model: str = "all-MiniLM-L6-v2",
    ) -> None:
        """Initialize the Memory Agent.

        Args:
            db_path: Path to the LanceDB database directory.
            embedding_model: Name of the sentence-transformers model.
        """
        self.embedding_generator = EmbeddingGenerator(embedding_model)
        self.store = LanceDBStore(
            db_path=db_path,
            embedding_dim=self.embedding_generator.embedding_dim,
        )

    async def add_documents(
        self,
        chunks: list[ParsedChunk],
        source_metadata: dict[str, Any],
    ) -> list[str]:
        """Store chunks with embeddings in the vector database.

        Args:
            chunks: List of parsed chunks to store.
            source_metadata: Metadata about the source document.

        Returns:
            List of chunk IDs that were stored.
        """
        if not chunks:
            return []

        # Extract data from chunks
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        contents = [chunk.content for chunk in chunks]
        source_id = source_metadata.get("source_id", "unknown")
        source_url = source_metadata.get("url")

        # Generate embeddings for all chunks
        embeddings = self.embedding_generator.embed_batch(contents)

        # Prepare metadata for each chunk
        metadata_list = []
        for chunk in chunks:
            chunk_metadata = {
                "chunk_index": chunk.chunk_index,
                "layout_type": chunk.layout_type,
                "page_number": chunk.page_number,
                **source_metadata,  # Include all source metadata
            }
            metadata_list.append(chunk_metadata)

        # Store in LanceDB
        await self.store.add_documents(
            chunk_ids=chunk_ids,
            contents=contents,
            embeddings=embeddings,
            source_ids=[source_id] * len(chunks),
            source_urls=[source_url] * len(chunks),
            metadata_list=metadata_list,
        )

        return chunk_ids

    async def query(
        self,
        query: MemoryQuery,
    ) -> MemoryOutput | AgentFailure:
        """Perform semantic search for relevant chunks.

        Args:
            query: The memory query with search parameters.

        Returns:
            MemoryOutput with retrieved contexts or AgentFailure.
        """
        # Generate query embedding
        query_embedding = self.embedding_generator.embed_text(query.query_text)

        # Search in LanceDB
        return await self.store.search(
            query_embedding=query_embedding,
            top_k=query.top_k,
            min_score=query.min_relevance_score,
            filters=query.filters,
        )

    async def delete_by_source(self, source_id: str) -> int:
        """Delete all chunks from a specific source document.

        Args:
            source_id: The source document identifier.

        Returns:
            Number of chunks deleted.
        """
        return await self.store.delete_by_source(source_id)

    async def count_documents(self) -> int:
        """Return the total number of stored chunks."""
        return await self.store.count_documents()
