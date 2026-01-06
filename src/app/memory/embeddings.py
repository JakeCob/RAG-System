"""Embedding generation utilities for the Memory Agent.

Uses sentence-transformers for generating semantic embeddings.
Reference: docs/02_AGENT_SPECS.md Section 2.3
"""

from typing import Any

from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:
    """Generate embeddings using sentence-transformers.

    The default model 'all-MiniLM-L6-v2' produces 384-dim vectors
    and is optimized for semantic search tasks.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Initialize the embedding model.

        Args:
            model_name: Name of the sentence-transformers model to use.
        """
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the sentence transformer model."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text string.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        embedding: Any = self.model.encode(text, convert_to_numpy=True)
        # Convert numpy array to list for LanceDB compatibility
        result: list[float] = embedding.tolist()
        return result

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        embeddings: Any = self.model.encode(
            texts, convert_to_numpy=True, show_progress_bar=False
        )
        result: list[list[float]] = embeddings.tolist()
        return result

    @property
    def embedding_dim(self) -> int:
        """Get the dimension of the embedding vectors."""
        dim = self.model.get_sentence_embedding_dimension()
        if dim is None:
            return 384  # Default dimension for all-MiniLM-L6-v2
        return int(dim)
