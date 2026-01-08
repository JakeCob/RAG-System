"""Pytest configuration and shared fixtures.

This module provides fixtures for:
- Mock LLM client (Section 2.1/2.2 of TEST_PLAN.md)
- Mock Vector DB / LanceDB (Section 2.3 of TEST_PLAN.md)
- Mock GDrive service (Section 2.1 of TEST_PLAN.md)
- Mock Crawler (Section 2.2 of TEST_PLAN.md)
- Test configuration

Reference: docs/04_TEST_PLAN.md Section 2
"""

import re
from collections.abc import AsyncGenerator
from typing import Any

import pytest

from tests.mocks.data_generators import (
    BROKEN_ENCODING_HTML,
    CLEANED_MARKDOWN_GOV_SITE,
    MALFORMED_PDF_BYTES,
    RAW_HTML_GOV_SITE,
    MockCrawlResult,
    generate_mock_pdf_bytes,
)
from tests.mocks.mock_llm import MockLLMClient
from tests.mocks.mock_vectordb import MockLanceDB


# =============================================================================
# Data Source Mocks (P1-2: The Fake Internet)
# =============================================================================


@pytest.fixture(autouse=True)
def _mock_embeddings_for_tests(request, monkeypatch) -> None:  # noqa: C901
    """Stub embedding generation for tests to avoid model downloads."""
    from app.memory.embeddings import EmbeddingGenerator
    from app.schemas import AgentFailure, ErrorCodes, MemoryOutput, RetrievedContext

    class _StubLanceDBStore:
        def __init__(self, db_path: str, embedding_dim: int = 384) -> None:
            self._docs: list[dict[str, Any]] = []
            self._db_path = db_path
            self._embedding_dim = embedding_dim

        async def add_documents(
            self,
            chunk_ids: list[str],
            contents: list[str],
            embeddings: list[list[float]],
            source_ids: list[str],
            source_urls: list[str | None],
            metadata_list: list[dict[str, Any]],
        ) -> None:
            for chunk_id, content, embedding, src_id, src_url, meta in zip(
                chunk_ids,
                contents,
                embeddings,
                source_ids,
                source_urls,
                metadata_list,
                strict=True,
            ):
                self._docs.append(
                    {
                        "chunk_id": chunk_id,
                        "content": content,
                        "embedding": embedding,
                        "source_id": src_id,
                        "source_url": src_url,
                        "metadata": meta,
                    }
                )

        async def search(
            self,
            query_embedding: list[float],
            top_k: int = 5,
            min_score: float = 0.7,
            filters: dict[str, Any] | None = None,
        ) -> MemoryOutput | AgentFailure:
            results: list[RetrievedContext] = []
            scored_docs: list[tuple[float, dict[str, Any]]] = []
            for doc in self._docs:
                if filters and not all(
                    doc.get("metadata", {}).get(k) == v for k, v in filters.items()
                ):
                    continue

                raw_score = self._cosine_similarity(
                    query_embedding, doc.get("embedding", [])
                )
                score = 0.8 + (0.2 * raw_score)
                if score >= min_score:
                    scored_docs.append((score, doc))

            scored_docs.sort(key=lambda item: item[0], reverse=True)
            for score, doc in scored_docs[:top_k]:
                results.append(
                    RetrievedContext(
                        chunk_id=doc["chunk_id"],
                        content=doc["content"],
                        source_id=doc["source_id"],
                        source_url=doc["source_url"],
                        relevance_score=score,
                        metadata=doc.get("metadata", {}),
                    )
                )

            if not results:
                return AgentFailure(
                    agent_id="memory",
                    error_code=ErrorCodes.MEMORY_NO_RESULTS,
                    message=f"No results above threshold {min_score}",
                    recoverable=True,
                )

            return MemoryOutput(results=results, total_found=len(results))

        async def delete_by_source(self, source_id: str) -> int:
            before = len(self._docs)
            self._docs = [doc for doc in self._docs if doc["source_id"] != source_id]
            return before - len(self._docs)

        def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
            if not left or not right:
                return 0.0
            dot = sum(a * b for a, b in zip(left, right, strict=False))
            left_norm = sum(a * a for a in left) ** 0.5
            right_norm = sum(b * b for b in right) ** 0.5
            if left_norm == 0 or right_norm == 0:
                return 0.0
            return dot / (left_norm * right_norm)

    dim = 8
    keyword_features = [
        "ai",
        "artificial",
        "intelligence",
        "neural",
        "learning",
        "network",
    ]

    def _embed_text(self, text: str) -> list[float]:
        lowered = text.lower()
        features = [float(lowered.count(keyword)) for keyword in keyword_features]
        features.append(float(len(lowered)) / 100.0)
        if len(features) < dim:
            features.extend([0.0] * (dim - len(features)))
        return features[:dim]

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [_embed_text(self, text) for text in texts]

    skip_embedding_stub = request.node.get_closest_marker("real_embeddings") is not None
    if not skip_embedding_stub:
        monkeypatch.setattr(EmbeddingGenerator, "embed_text", _embed_text, raising=True)
        monkeypatch.setattr(
            EmbeddingGenerator, "embed_batch", _embed_batch, raising=True
        )
        monkeypatch.setattr(
            EmbeddingGenerator,
            "embedding_dim",
            property(lambda _: dim),
            raising=False,
        )
    monkeypatch.setattr(
        "app.memory.agent.LanceDBStore",
        _StubLanceDBStore,
        raising=False,
    )
    monkeypatch.setattr(
        "app.memory.lancedb_store.LanceDBStore",
        _StubLanceDBStore,
        raising=False,
    )

    if request.node.get_closest_marker("integration"):

        class _StubLLMService:
            async def generate(
                self,
                *,
                prompt: str,
                system: str | None = None,
                temperature: float | None = None,
                max_tokens: int | None = None,
            ) -> str:
                _ = system
                _ = temperature
                _ = max_tokens

                context_section = ""
                if "Context:" in prompt:
                    context_section = prompt.split("Context:", 1)[1]
                matches = re.findall(r"\[(\d+)\]", context_section)
                citations = sorted({int(match) for match in matches})
                citation_text = " ".join(f"[{idx}]" for idx in citations) or "[1]"
                if "May" in prompt:
                    return f"Project timeline includes May. {citation_text}"
                return f"Stub response. {citation_text}"

        monkeypatch.setattr(
            "app.services.llm.LLMService",
            _StubLLMService,
            raising=False,
        )
        monkeypatch.setattr(
            "app.agents.tailor.LLMService",
            _StubLLMService,
            raising=False,
        )
        monkeypatch.setattr(
            "app.agents.orchestrator.LLMService",
            _StubLLMService,
            raising=False,
        )


@pytest.fixture
def mock_web_content() -> dict[str, str]:
    """Provide raw HTML and expected Markdown for a simulated government site.

    Returns:
        dict: Keys 'html' (raw) and 'markdown' (cleaned).
    """
    return {
        "html": RAW_HTML_GOV_SITE,
        "markdown": CLEANED_MARKDOWN_GOV_SITE,
    }


@pytest.fixture
def mock_broken_web_content() -> bytes:
    """Provide a byte string with mixed encoding issues.

    Returns:
        bytes: Raw content with latin-1 and utf-8 mix.
    """
    return BROKEN_ENCODING_HTML


@pytest.fixture
def mock_pdf_file():
    """Provide a BytesIO object simulating a loaded PDF file.

    Returns:
        BytesIO: A stream containing valid PDF bytes.
    """
    return generate_mock_pdf_bytes()


@pytest.fixture
def mock_malformed_pdf_file() -> bytes:
    """Provide a byte string simulating a corrupted PDF file.

    Returns:
        bytes: Invalid PDF content.
    """
    return MALFORMED_PDF_BYTES


@pytest.fixture
def mock_crawl_result(mock_web_content) -> MockCrawlResult:
    """Provide a mock result object matching crawl4ai's output structure.

    Args:
        mock_web_content: Fixture providing the content.

    Returns:
        MockCrawlResult: Pydantic object with markdown and metadata.
    """
    return MockCrawlResult(
        markdown=mock_web_content["markdown"],
        url="https://gov.local/notice/123",
        metadata={
            "title": "Department of Bureaucracy - Public Notice 123",
            "date": "2025-01-15",
            "language": "en",
        },
        html=mock_web_content["html"],
        success=True,
    )


# =============================================================================
# LLM Mocks (TEST_PLAN.md Section 2.1/2.2)
# =============================================================================


@pytest.fixture
def mock_llm() -> MockLLMClient:
    """Provide a fresh MockLLMClient for each test."""
    return MockLLMClient()


@pytest.fixture
def mock_llm_with_responses() -> MockLLMClient:
    """Provide MockLLMClient with predefined responses."""
    return MockLLMClient(
        responses={
            "summarize": "This is a mock summary.",
            "answer": "This is a mock answer based on the context.",
        }
    )


# =============================================================================
# Vector DB Mocks (TEST_PLAN.md Section 2.3)
# =============================================================================


@pytest.fixture
def mock_vector_db() -> MockLanceDB:
    """Provide a fresh MockLanceDB for each test.

    Reference: docs/04_TEST_PLAN.md Section 2.3
    Fixture automatically wipes the DB after each test function.
    """
    return MockLanceDB()


@pytest.fixture
async def populated_vector_db() -> AsyncGenerator[MockLanceDB, None]:
    """Provide MockLanceDB with sample documents pre-seeded.

    Contains sample data for deterministic test results.
    """
    db = MockLanceDB()
    await db.add_documents(
        documents=[
            "Python is a programming language.",
            "FastAPI is a web framework for Python.",
            "LanceDB is a vector database for AI applications.",
        ],
        embeddings=[
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9],
        ],
        metadata=[
            {"source_type": "local", "url": None},
            {"source_type": "gdrive", "url": "https://drive.google.com/doc1"},
            {"source_type": "web", "url": "https://lancedb.dev"},
        ],
        source_ids=["doc_python", "doc_fastapi", "doc_lancedb"],
    )
    yield db
    db.reset()


# =============================================================================
# GDrive Mocks (TEST_PLAN.md Section 2.1)
# =============================================================================


@pytest.fixture
def mock_gdrive_service() -> dict[str, Any]:
    """Mock Google Drive API service.

    Reference: docs/04_TEST_PLAN.md Section 2.1
    Intercepts calls to googleapiclient.discovery.build.
    """
    return {
        "files_list": {
            "files": [{"id": "123", "name": "test.pdf", "mimeType": "application/pdf"}]
        },
        "files_list_empty": {"files": []},
        "auth_error": {"error": {"code": 401, "message": "Invalid credentials"}},
    }


# =============================================================================
# Web Crawler Mocks (TEST_PLAN.md Section 2.2)
# =============================================================================


@pytest.fixture
def mock_crawler_responses() -> dict[str, Any]:
    """Mock web crawler responses.

    Reference: docs/04_TEST_PLAN.md Section 2.2
    """
    return {
        "success": {
            "html": "<html><body><h1>Test</h1><p>Content</p></body></html>",
            "text": "# Test\n\nContent",
            "metadata": {"title": "Test Page", "url": "https://example.com"},
        },
        "forbidden": {"error": "403 Forbidden"},
        "not_found": {"error": "404 Not Found"},
        "malicious": {
            "html": "<body><script>alert('xss')</script><p>Safe</p></body>",
            "text": "Safe content",
            "metadata": {"title": "Malicious Page"},
        },
    }


# =============================================================================
# Test Configuration
# =============================================================================


@pytest.fixture
def sample_embedding() -> list[float]:
    """Provide a sample embedding vector (384-dim truncated for tests)."""
    return [0.1, 0.2, 0.3]


@pytest.fixture
def test_config() -> dict[str, Any]:
    """Provide test configuration values matching INGESTION_STRATEGY.md."""
    return {
        "llm_model": "mock-model",
        "embedding_model": "mock-embeddings",
        "chunk_size": 512,  # Per INGESTION_STRATEGY.md Section 5
        "chunk_overlap": 50,  # 10% overlap
        "max_chunk_tokens": 1024,
        "min_relevance_score": 0.7,
        "max_recursion_depth": 5,  # Per DESIGN_DOC.md
    }
