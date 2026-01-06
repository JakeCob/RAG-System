"""Deterministic Memory Agent implementation.

Provides a lightweight, fully in-memory vector store that satisfies the
contracts defined in docs/02_AGENT_SPECS.md. The agent supports ingestion of
`ParserOutput` objects and returns `RetrievedContext` instances for the ROMA
orchestrator. All operations are async-friendly (even though the store is
purely in memory) to match the rest of the application stack.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from app.exceptions import AgentFailureError
from app.schemas import (
    ErrorCodes,
    MemoryOutput,
    MemoryQuery,
    ParsedChunk,
    ParserOutput,
    RetrievedContext,
)
from app.schemas.base import SourceType

_TOKEN_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(slots=True)
class _StoredChunk:
    """Internal representation of an indexed chunk."""

    chunk_id: str
    document_id: str
    content: str
    source_id: str
    source_url: str | None
    metadata: dict[str, Any]
    tokens: set[str] = field(default_factory=set)


class InMemoryVectorStore:
    """Simple in-memory vector store used across tests and the API."""

    def __init__(self) -> None:
        self._records: dict[str, _StoredChunk] = {}

    def batch_upsert(self, records: Sequence[_StoredChunk]) -> None:
        """Insert or update a collection of stored chunks."""

        for record in records:
            self._records[record.chunk_id] = record

    def clear(self) -> None:
        """Remove all stored chunks (useful for tests)."""

        self._records.clear()

    def query(self, query: MemoryQuery) -> MemoryOutput:
        """Execute a similarity-style search against stored records."""

        query_terms = _tokenize(query.query_text)
        matches: list[tuple[float, _StoredChunk]] = []

        for record in self._records.values():
            if not _match_filters(record.metadata, query.filters):
                continue
            score = _score_record(query_terms, record.tokens)
            if score >= query.min_relevance_score:
                matches.append((score, record))

        matches.sort(key=lambda item: item[0], reverse=True)
        contexts = [
            RetrievedContext(
                chunk_id=record.chunk_id,
                content=record.content,
                source_id=record.source_id,
                source_url=record.source_url,
                relevance_score=round(score, 3),
                metadata=dict(record.metadata),
            )
            for score, record in matches[: query.top_k]
        ]
        return MemoryOutput(results=contexts, total_found=len(contexts))


class MemoryAgent:
    """Memory/Vector storage layer for the RAG system."""

    def __init__(
        self,
        *,
        agent_id: str = "memory",
        store: InMemoryVectorStore | None = None,
        bootstrap_documents: bool = False,
    ) -> None:
        self._agent_id = agent_id
        self._store = store or InMemoryVectorStore()
        if bootstrap_documents:
            self._store.batch_upsert(_default_seed_records())

    async def index_parser_output(
        self,
        parser_output: ParserOutput,
        *,
        source_id: str,
        source_type: SourceType,
        source_url: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """Index a parsed document into the vector store."""

        records = _records_from_parser_output(
            parser_output,
            source_id=source_id,
            source_type=source_type,
            source_url=source_url,
            extra_metadata=extra_metadata,
        )
        self._store.batch_upsert(records)
        return [record.chunk_id for record in records]

    def load_contexts(self, contexts: Sequence[RetrievedContext]) -> None:
        """Synchronously load pre-built contexts (used for bootstrapping)."""

        records = [_record_from_context(context) for context in contexts]
        self._store.batch_upsert(records)

    async def retrieve(
        self,
        *,
        query_text: str,
        top_k: int = 5,
        min_relevance_score: float = 0.7,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedContext]:
        """Return relevant context chunks or raise AgentFailureError."""

        query = MemoryQuery(
            query_text=query_text,
            top_k=top_k,
            min_relevance_score=min_relevance_score,
            filters=filters,
        )
        output = self._store.query(query)
        if not output.results:
            raise AgentFailureError(
                agent_id=self._agent_id,
                error_code=ErrorCodes.MEMORY_NO_RESULTS,
                message="No relevant chunks found for query.",
                recoverable=True,
            )
        return output.results

    async def search(self, query: MemoryQuery) -> MemoryOutput:
        """Execute a MemoryQuery object (useful for tests and tools)."""

        output = self._store.query(query)
        if not output.results:
            raise AgentFailureError(
                agent_id=self._agent_id,
                error_code=ErrorCodes.MEMORY_NO_RESULTS,
                message="No relevant chunks found for query.",
                recoverable=True,
            )
        return output

    def reset(self) -> None:
        """Clear all stored documents (used in test isolation)."""

        self._store.clear()


def _records_from_parser_output(
    parser_output: ParserOutput,
    *,
    source_id: str,
    source_type: SourceType,
    source_url: str | None,
    extra_metadata: dict[str, Any] | None,
) -> list[_StoredChunk]:
    """Convert ParserOutput chunks into stored chunk records."""

    base_metadata: dict[str, Any] = dict(parser_output.metadata)
    base_metadata.setdefault("document_id", parser_output.document_id)
    base_metadata.setdefault("source_type", source_type)
    if extra_metadata:
        base_metadata.update(extra_metadata)

    records: list[_StoredChunk] = []
    for chunk in parser_output.chunks:
        chunk_metadata = dict(base_metadata)
        chunk_metadata["chunk_index"] = chunk.chunk_index
        chunk_metadata["layout_type"] = chunk.layout_type
        tokens = _tokenize(chunk.content)
        tokens.update(_tokens_from_metadata(chunk_metadata))
        records.append(
            _StoredChunk(
                chunk_id=chunk.chunk_id,
                document_id=parser_output.document_id,
                content=chunk.content,
                source_id=source_id,
                source_url=source_url or base_metadata.get("url"),
                metadata=chunk_metadata,
                tokens=tokens,
            )
        )
    return records


def _record_from_context(context: RetrievedContext) -> _StoredChunk:
    """Convert a RetrievedContext into a stored chunk for seeding."""

    metadata = dict(context.metadata)
    metadata.setdefault("document_id", metadata.get("source_id", context.source_id))
    tokens = _tokenize(context.content)
    tokens.update(_tokens_from_metadata(metadata))
    return _StoredChunk(
        chunk_id=context.chunk_id,
        document_id=str(metadata.get("document_id")),
        content=context.content,
        source_id=context.source_id,
        source_url=context.source_url,
        metadata=metadata,
        tokens=tokens,
    )


def _match_filters(
    metadata: Mapping[str, Any], filters: Mapping[str, Any] | None
) -> bool:
    if not filters:
        return True
    for key, expected in filters.items():
        if metadata.get(key) != expected:
            return False
    return True


def _score_record(query_terms: Iterable[str], tokens: set[str]) -> float:
    query_terms = set(query_terms)
    if not query_terms:
        return 0.85
    overlap = sum(1 for term in query_terms if term in tokens)
    coverage = overlap / len(query_terms)
    base = 0.35 + (0.55 * coverage)
    if overlap > 0:
        base += 0.1
    if coverage == 1.0:
        base += 0.05
    return round(min(base, 0.99), 3)


def _tokenize(text: str) -> set[str]:
    return {token for token in _TOKEN_PATTERN.split(text.lower()) if token}


def _tokens_from_metadata(metadata: Mapping[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for value in metadata.values():
        if isinstance(value, str):
            tokens.update(_tokenize(value))
        elif isinstance(value, (int, float)):
            tokens.add(str(value))
    return tokens


def _default_seed_records() -> list[_StoredChunk]:
    """Return deterministic bootstrap documents for the API surface."""

    seeds = [
        {
            "chunk_id": "seed-roma-overview",
            "document_id": "roma_overview",
            "source_id": "roma_design_doc",
            "source_url": "https://docs.local/roma",
            "content": (
                "Hello! The ROMA orchestrator relies on guardrails, LanceDB-style "
                "memory retrieval, and the Tailor agent to craft grounded answers."
            ),
            "metadata": {
                "source_type": "local",
                "ingestion_source": "bootstrap",
                "document_id": "roma_overview",
            },
        },
        {
            "chunk_id": "seed-streaming",
            "document_id": "streaming_playbook",
            "source_id": "tailor_playbook",
            "source_url": "https://docs.local/streaming",
            "content": (
                "Streaming responses keep the chat UI responsive; stream tokens "
                "come directly from the Tailor agent and are validated by guardrails."
            ),
            "metadata": {
                "source_type": "web",
                "ingestion_source": "bootstrap",
                "document_id": "streaming_playbook",
            },
        },
    ]

    records: list[_StoredChunk] = []
    for seed in seeds:
        metadata = dict(seed["metadata"])
        tokens = _tokenize(seed["content"])
        tokens.update(_tokens_from_metadata(metadata))
        records.append(
            _StoredChunk(
                chunk_id=seed["chunk_id"],
                document_id=seed["document_id"],
                content=seed["content"],
                source_id=seed["source_id"],
                source_url=seed["source_url"],
                metadata=metadata,
                tokens=tokens,
            )
        )
    return records


__all__ = ["InMemoryVectorStore", "MemoryAgent"]
