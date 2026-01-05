"""Pytest configuration and shared fixtures.

This module provides fixtures for:
- Mock LLM client (Section 2.1/2.2 of TEST_PLAN.md)
- Mock Vector DB / LanceDB (Section 2.3 of TEST_PLAN.md)
- Mock GDrive service (Section 2.1 of TEST_PLAN.md)
- Mock Crawler (Section 2.2 of TEST_PLAN.md)
- Test configuration

Reference: docs/04_TEST_PLAN.md Section 2
"""

from collections.abc import AsyncGenerator
from typing import Any

import pytest

from tests.mocks.mock_llm import MockLLMClient
from tests.mocks.mock_vectordb import MockLanceDB
from tests.mocks.data_generators import (
    RAW_HTML_GOV_SITE,
    CLEANED_MARKDOWN_GOV_SITE,
    BROKEN_ENCODING_HTML,
    MALFORMED_PDF_BYTES,
    generate_mock_pdf_bytes,
    MockCrawlResult,
)


# =============================================================================
# Data Source Mocks (P1-2: The Fake Internet)
# =============================================================================


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
