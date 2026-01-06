"""RAG Engine - The Brain of the system.

Handles retrieval from vector store and answer generation via LLM.
Reference: Phase 2-2 RAG Engine Implementation
"""

from typing import Any, Protocol

from brain.schemas import (
    Answer,
    Citation,
    ContextNode,
    GenerateConfig,
    QueryConfig,
    QueryResult,
    RAGErrorCodes,
    RAGFailure,
)


class VectorStoreProtocol(Protocol):
    """Protocol for vector store implementations."""

    async def search(
        self, query: str, top_k: int = 5, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        ...


class LLMClientProtocol(Protocol):
    """Protocol for LLM client implementations."""

    async def complete(self, prompt: str) -> str:
        ...


# Approximate tokens per character (conservative estimate)
CHARS_PER_TOKEN = 4


class RAGEngine:
    """RAG Engine for retrieval-augmented generation.

    Provides:
    - retrieve(): Get relevant context from vector store
    - generate_answer(): Generate answer from context using LLM
    - query(): Unified retrieve + generate pipeline
    """

    def __init__(
        self,
        vector_store: Any,
        llm_client: Any,
        default_config: QueryConfig | None = None,
    ) -> None:
        """Initialize the RAG Engine.

        Args:
            vector_store: Vector store with async search(query, top_k, filters)
            llm_client: LLM client with async complete(prompt)
            default_config: Default configuration for queries
        """
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.default_config = default_config or QueryConfig()

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        min_score: float | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[ContextNode] | RAGFailure:
        """Retrieve relevant context from the vector store.

        Args:
            query: The search query
            top_k: Maximum number of results (default: from config)
            min_score: Minimum relevance score threshold (default: from config)
            filters: Optional metadata filters

        Returns:
            List of ContextNode objects or RAGFailure on error
        """
        if not query or not query.strip():
            return RAGFailure(
                error_code=RAGErrorCodes.INVALID_QUERY,
                message="Query cannot be empty",
                recoverable=False,
            )

        # Use provided values or fall back to config defaults
        config_top_k = self.default_config.retrieve.top_k
        effective_top_k = top_k if top_k is not None else config_top_k
        config_min_score = self.default_config.retrieve.min_score
        effective_min_score = min_score if min_score is not None else config_min_score
        effective_filters = filters or self.default_config.retrieve.filters

        try:
            # Call vector store - handle both simple and complex signatures
            if effective_filters is not None:
                try:
                    results = await self.vector_store.search(
                        query, top_k=effective_top_k, filters=effective_filters
                    )
                except TypeError:
                    # Fallback for simple search(query) signature
                    results = await self.vector_store.search(query)
            else:
                try:
                    results = await self.vector_store.search(
                        query, top_k=effective_top_k
                    )
                except TypeError:
                    # Fallback for simple search(query) signature
                    results = await self.vector_store.search(query)

        except Exception as e:
            return RAGFailure(
                error_code=RAGErrorCodes.RETRIEVAL_FAILED,
                message=f"Vector store search failed: {e!s}",
                recoverable=True,
                details={"query": query, "error": str(e)},
            )

        # Convert results to ContextNode objects
        nodes = []
        for res in results:
            metadata = res.get("metadata", {})
            node = ContextNode(
                id=res.get("id", ""),
                text=res.get("content", ""),
                score=res.get("score", 0.0),
                source_id=metadata.get("source", res.get("id", "")),
                source_url=metadata.get("url"),
                metadata=metadata,
            )
            # Apply minimum score filter
            if node.score >= effective_min_score:
                nodes.append(node)

        return nodes

    async def generate_answer(
        self,
        query: str,
        context: list[ContextNode],
        config: GenerateConfig | None = None,
    ) -> Answer | RAGFailure:
        """Generate an answer using the LLM with provided context.

        Args:
            query: The user's question
            context: List of ContextNode objects to use as context
            config: Optional generation configuration

        Returns:
            Answer object or RAGFailure on error
        """
        effective_config = config or self.default_config.generate

        # Truncate context if needed to fit token limit
        truncated_context = self._truncate_context(
            context, effective_config.max_context_tokens
        )

        # Build the prompt
        prompt = self._build_prompt(
            query, truncated_context, effective_config.system_prompt
        )

        try:
            response_text = await self.llm_client.complete(prompt)
        except Exception as e:
            return RAGFailure(
                error_code=RAGErrorCodes.LLM_FAILED,
                message=f"LLM completion failed: {e!s}",
                recoverable=True,
                details={"query": query, "error": str(e)},
            )

        # Build citations if enabled
        citations: list[Citation] = []
        if effective_config.include_citations:
            citations = self._build_citations(truncated_context)

        # Calculate confidence based on context quality
        confidence = self._calculate_confidence(truncated_context)

        return Answer(
            content=response_text,
            citations=citations,
            tone_used=effective_config.persona,
            follow_up_suggestions=[],  # Can be populated by LLM in future
            confidence_score=confidence,
            metadata={
                "model": "rag-engine-v2",
                "context_count": len(truncated_context),
                "truncated": len(truncated_context) < len(context),
            },
        )

    async def query(
        self,
        query: str,
        config: QueryConfig | None = None,
    ) -> QueryResult | RAGFailure:
        """Execute a full RAG query: retrieve context and generate answer.

        This is the unified entrypoint that combines retrieve() and generate_answer().

        Args:
            query: The user's question
            config: Optional query configuration

        Returns:
            QueryResult with answer and metadata, or RAGFailure on error
        """
        effective_config = config or self.default_config

        # Step 1: Retrieve relevant context
        retrieve_result = await self.retrieve(
            query,
            top_k=effective_config.retrieve.top_k,
            min_score=effective_config.retrieve.min_score,
            filters=effective_config.retrieve.filters,
        )

        if isinstance(retrieve_result, RAGFailure):
            return retrieve_result

        context_nodes = retrieve_result
        retrieval_count = len(context_nodes)

        # Check if we have any relevant context
        if not context_nodes:
            min_score = effective_config.retrieve.min_score
            return RAGFailure(
                error_code=RAGErrorCodes.NO_RELEVANT_CONTEXT,
                message=f"No context found above min_score={min_score}",
                recoverable=True,
                details={
                    "query": query,
                    "top_k": effective_config.retrieve.top_k,
                },
            )

        # Step 2: Generate answer
        answer_result = await self.generate_answer(
            query, context_nodes, effective_config.generate
        )

        if isinstance(answer_result, RAGFailure):
            return answer_result

        return QueryResult(
            answer=answer_result,
            context_used=context_nodes,
            retrieval_count=retrieval_count,
            filtered_count=retrieval_count,  # After min_score filter
            metadata={
                "config": effective_config.model_dump(),
            },
        )

    def _truncate_context(
        self, context: list[ContextNode], max_tokens: int
    ) -> list[ContextNode]:
        """Truncate context to fit within token limit.

        Uses a conservative character-to-token estimate.
        Prioritizes higher-scored context nodes.
        """
        # Sort by score descending to keep best context
        sorted_context = sorted(context, key=lambda x: x.score, reverse=True)

        max_chars = max_tokens * CHARS_PER_TOKEN
        current_chars = 0
        truncated: list[ContextNode] = []

        for node in sorted_context:
            node_chars = len(node.text)
            if current_chars + node_chars <= max_chars:
                truncated.append(node)
                current_chars += node_chars
            else:
                # Stop adding more context
                break

        return truncated

    def _build_prompt(
        self,
        query: str,
        context: list[ContextNode],
        system_prompt: str | None = None,
    ) -> str:
        """Build the prompt for the LLM."""
        parts = []

        if system_prompt:
            parts.append(system_prompt)
            parts.append("")

        if context:
            context_str = "\n".join([f"- {node.text}" for node in context])
            parts.append(f"Context:\n{context_str}")
            parts.append("")

        parts.append(f"Query: {query}")

        return "\n".join(parts)

    def _build_citations(self, context: list[ContextNode]) -> list[Citation]:
        """Build citations from context nodes."""
        citations = []
        for node in context:
            # Prefer url > source_id > node.id for source_id
            source_id = node.source_url or node.source_id or node.id
            # Build text snippet (truncated for readability)
            snippet = node.text[:100] + "..." if len(node.text) > 100 else node.text
            citation = Citation(
                source_id=source_id,
                chunk_id=node.id,
                text_snippet=snippet,
                url=node.source_url,
            )
            citations.append(citation)
        return citations

    def _calculate_confidence(self, context: list[ContextNode]) -> float:
        """Calculate confidence score based on context quality.

        Uses average relevance score of context nodes.
        Returns 0.5 if no context (uncertain).
        """
        if not context:
            return 0.5
        avg_score = sum(node.score for node in context) / len(context)
        return min(1.0, max(0.0, avg_score))
