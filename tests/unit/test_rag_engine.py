"""RAG Engine (Brain) tests.

Reference: Phase 2-2 RAG Engine Implementation
Tests for retrieval, answer generation, and unified query pipeline.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.brain.engine import RAGEngine
from src.brain.schemas import (
    Answer,
    Citation,
    ContextNode,
    GenerateConfig,
    QueryConfig,
    QueryResult,
    RAGErrorCodes,
    RAGFailure,
    RetrieveConfig,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_vector_store():
    """Mock vector store with async search method."""
    m = MagicMock()
    m.search = AsyncMock()
    return m


@pytest.fixture
def mock_llm_client():
    """Mock LLM client with async complete method."""
    m = MagicMock()
    m.complete = AsyncMock()
    return m


@pytest.fixture
def rag_engine(mock_vector_store, mock_llm_client):
    """RAG engine with default configuration."""
    return RAGEngine(vector_store=mock_vector_store, llm_client=mock_llm_client)


@pytest.fixture
def mock_context_data():
    """Sample context nodes for testing."""
    return [
        ContextNode(
            id="1",
            text="The sky is blue.",
            score=0.9,
            source_id="doc1",
            source_url="http://example.com/doc1",
            metadata={"source": "doc1", "url": "http://example.com/doc1"},
        ),
        ContextNode(
            id="2",
            text="Grass is green.",
            score=0.8,
            source_id="doc2",
            source_url="http://example.com/doc2",
            metadata={"source": "doc2", "url": "http://example.com/doc2"},
        ),
    ]


@pytest.fixture
def mock_search_results():
    """Sample search results from vector store."""
    return [
        {
            "id": "1",
            "content": "The sky is blue.",
            "score": 0.9,
            "metadata": {"source": "doc1"},
        },
        {
            "id": "2",
            "content": "Grass is green.",
            "score": 0.8,
            "metadata": {"source": "doc2"},
        },
    ]


# =============================================================================
# Basic Retrieve Tests (Original)
# =============================================================================


@pytest.mark.asyncio
async def test_retrieve_calls_vector_store_and_returns_context_nodes(
    rag_engine, mock_vector_store, mock_search_results
):
    """Test that retrieve calls vector store and returns ContextNode list."""
    # Arrange
    query = "What is the color of the sky?"
    mock_vector_store.search.return_value = mock_search_results

    # Act
    results = await rag_engine.retrieve(query)

    # Assert
    mock_vector_store.search.assert_awaited_once()
    args, _ = mock_vector_store.search.call_args
    assert query in args[0] or query == args[0]

    assert isinstance(results, list)
    assert len(results) == 2
    assert all(isinstance(node, ContextNode) for node in results)
    assert results[0].text == "The sky is blue."
    assert results[0].id == "1"


# =============================================================================
# Basic Generate Answer Tests (Original)
# =============================================================================


@pytest.mark.asyncio
async def test_generate_answer_constructs_prompt_with_query_and_context(
    rag_engine, mock_llm_client, mock_context_data
):
    """Test that generate_answer includes query and context in the prompt."""
    # Arrange
    query = "What colors are mentioned?"
    mock_llm_client.complete.return_value = "Blue and Green."

    # Act
    await rag_engine.generate_answer(query, mock_context_data)

    # Assert
    mock_llm_client.complete.assert_awaited()
    call_args = mock_llm_client.complete.call_args
    call_args_str = str(call_args)

    assert query in call_args_str
    assert "The sky is blue" in call_args_str
    assert "Grass is green" in call_args_str


@pytest.mark.asyncio
async def test_generate_answer_returns_strict_answer_object(
    rag_engine, mock_llm_client, mock_context_data
):
    """Test that generate_answer returns a proper Answer object."""
    # Arrange
    query = "What colors are mentioned?"
    mock_llm_client.complete.return_value = "Blue and Green."

    # Act
    answer = await rag_engine.generate_answer(query, mock_context_data)

    # Assert
    assert isinstance(answer, Answer)
    assert answer.content == "Blue and Green."
    assert isinstance(answer.citations, list)


@pytest.mark.asyncio
async def test_generate_answer_no_context(rag_engine, mock_llm_client):
    """Test that generate_answer handles empty context gracefully."""
    # Arrange
    query = "Unknown topic"
    context = []
    mock_llm_client.complete.return_value = "I don't know."

    # Act
    answer = await rag_engine.generate_answer(query, context)

    # Assert
    assert isinstance(answer, Answer)
    assert answer.content


# =============================================================================
# NEW: Retrieve with Parameters Tests
# =============================================================================


@pytest.mark.asyncio
async def test_retrieve_with_top_k_parameter(
    rag_engine, mock_vector_store, mock_search_results
):
    """Test that retrieve respects top_k parameter."""
    # Arrange
    query = "test query"
    mock_vector_store.search.return_value = mock_search_results

    # Act
    await rag_engine.retrieve(query, top_k=10)

    # Assert
    mock_vector_store.search.assert_awaited_once()
    _, kwargs = mock_vector_store.search.call_args
    assert kwargs.get("top_k") == 10


@pytest.mark.asyncio
async def test_retrieve_with_min_score_filters_results(
    rag_engine, mock_vector_store
):
    """Test that retrieve filters results below min_score."""
    # Arrange
    query = "test query"
    mock_vector_store.search.return_value = [
        {"id": "1", "content": "High score", "score": 0.95, "metadata": {}},
        {"id": "2", "content": "Medium score", "score": 0.75, "metadata": {}},
        {"id": "3", "content": "Low score", "score": 0.4, "metadata": {}},
    ]

    # Act
    results = await rag_engine.retrieve(query, min_score=0.7)

    # Assert
    assert len(results) == 2
    assert all(node.score >= 0.7 for node in results)
    assert results[0].text == "High score"
    assert results[1].text == "Medium score"


@pytest.mark.asyncio
async def test_retrieve_uses_config_defaults(mock_vector_store, mock_llm_client):
    """Test that retrieve uses default config values."""
    # Arrange
    config = QueryConfig(
        retrieve=RetrieveConfig(top_k=3, min_score=0.5)
    )
    engine = RAGEngine(
        vector_store=mock_vector_store,
        llm_client=mock_llm_client,
        default_config=config,
    )
    mock_vector_store.search.return_value = [
        {"id": "1", "content": "Test", "score": 0.6, "metadata": {}},
    ]

    # Act
    await engine.retrieve("test query")

    # Assert
    _, kwargs = mock_vector_store.search.call_args
    assert kwargs.get("top_k") == 3


# =============================================================================
# NEW: Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
async def test_retrieve_empty_query_returns_failure(rag_engine):
    """Test that retrieve returns RAGFailure for empty query."""
    # Act
    result = await rag_engine.retrieve("")

    # Assert
    assert isinstance(result, RAGFailure)
    assert result.error_code == RAGErrorCodes.INVALID_QUERY
    assert result.recoverable is False


@pytest.mark.asyncio
async def test_retrieve_whitespace_query_returns_failure(rag_engine):
    """Test that retrieve returns RAGFailure for whitespace-only query."""
    # Act
    result = await rag_engine.retrieve("   ")

    # Assert
    assert isinstance(result, RAGFailure)
    assert result.error_code == RAGErrorCodes.INVALID_QUERY


@pytest.mark.asyncio
async def test_retrieve_vector_store_error_returns_failure(
    rag_engine, mock_vector_store
):
    """Test that retrieve returns RAGFailure when vector store fails."""
    # Arrange
    mock_vector_store.search.side_effect = Exception("Connection failed")

    # Act
    result = await rag_engine.retrieve("test query")

    # Assert
    assert isinstance(result, RAGFailure)
    assert result.error_code == RAGErrorCodes.RETRIEVAL_FAILED
    assert result.recoverable is True
    assert "Connection failed" in result.message


@pytest.mark.asyncio
async def test_generate_answer_llm_error_returns_failure(
    rag_engine, mock_llm_client, mock_context_data
):
    """Test that generate_answer returns RAGFailure when LLM fails."""
    # Arrange
    mock_llm_client.complete.side_effect = Exception("API rate limit")

    # Act
    result = await rag_engine.generate_answer("test query", mock_context_data)

    # Assert
    assert isinstance(result, RAGFailure)
    assert result.error_code == RAGErrorCodes.LLM_FAILED
    assert result.recoverable is True
    assert "API rate limit" in result.message


# =============================================================================
# NEW: Unified Query Method Tests
# =============================================================================


@pytest.mark.asyncio
async def test_query_returns_query_result(
    rag_engine, mock_vector_store, mock_llm_client, mock_search_results
):
    """Test that query() returns a complete QueryResult."""
    # Arrange
    mock_vector_store.search.return_value = mock_search_results
    mock_llm_client.complete.return_value = "The sky is blue and grass is green."

    # Act
    result = await rag_engine.query("What colors are mentioned?")

    # Assert
    assert isinstance(result, QueryResult)
    assert isinstance(result.answer, Answer)
    assert result.answer.content == "The sky is blue and grass is green."
    assert len(result.context_used) == 2
    assert result.retrieval_count == 2


@pytest.mark.asyncio
async def test_query_with_custom_config(
    mock_vector_store, mock_llm_client
):
    """Test that query() respects custom configuration."""
    # Arrange
    engine = RAGEngine(vector_store=mock_vector_store, llm_client=mock_llm_client)
    mock_vector_store.search.return_value = [
        {"id": "1", "content": "Test content", "score": 0.85, "metadata": {}},
    ]
    mock_llm_client.complete.return_value = "Answer"

    config = QueryConfig(
        retrieve=RetrieveConfig(top_k=10, min_score=0.8),
        generate=GenerateConfig(include_citations=True),
    )

    # Act
    result = await engine.query("test", config=config)

    # Assert
    assert isinstance(result, QueryResult)
    _, kwargs = mock_vector_store.search.call_args
    assert kwargs.get("top_k") == 10


@pytest.mark.asyncio
async def test_query_no_results_returns_failure(
    rag_engine, mock_vector_store
):
    """Test that query() returns RAGFailure when no relevant context found."""
    # Arrange
    mock_vector_store.search.return_value = []

    # Act
    result = await rag_engine.query("obscure topic")

    # Assert
    assert isinstance(result, RAGFailure)
    assert result.error_code == RAGErrorCodes.NO_RELEVANT_CONTEXT
    assert result.recoverable is True


@pytest.mark.asyncio
async def test_query_min_score_filters_all_returns_failure(
    mock_vector_store, mock_llm_client
):
    """Test that query returns failure when min_score filters out all results."""
    # Arrange
    config = QueryConfig(retrieve=RetrieveConfig(min_score=0.99))
    engine = RAGEngine(
        vector_store=mock_vector_store,
        llm_client=mock_llm_client,
        default_config=config,
    )
    mock_vector_store.search.return_value = [
        {"id": "1", "content": "Low score", "score": 0.5, "metadata": {}},
    ]

    # Act
    result = await engine.query("test")

    # Assert
    assert isinstance(result, RAGFailure)
    assert result.error_code == RAGErrorCodes.NO_RELEVANT_CONTEXT


# =============================================================================
# NEW: Context Truncation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_generate_answer_truncates_large_context(
    rag_engine, mock_llm_client
):
    """Test that large context is truncated to fit token limit."""
    # Arrange
    # Create context that exceeds default 4000 tokens (~16000 chars)
    large_context = [
        ContextNode(
            id=str(i),
            text="A" * 5000,  # 5000 chars each
            score=0.9 - (i * 0.1),
            metadata={},
        )
        for i in range(5)
    ]
    mock_llm_client.complete.return_value = "Truncated answer"

    config = GenerateConfig(max_context_tokens=1000)  # ~4000 chars

    # Act
    answer = await rag_engine.generate_answer("test", large_context, config=config)

    # Assert
    assert isinstance(answer, Answer)
    assert answer.metadata.get("truncated") is True
    # Should have included fewer than all 5 contexts
    assert answer.metadata.get("context_count", 0) < 5


@pytest.mark.asyncio
async def test_truncation_prioritizes_high_score_context(rag_engine, mock_llm_client):
    """Test that truncation keeps highest-scored context."""
    # Arrange
    context = [
        ContextNode(id="low", text="B" * 3000, score=0.5, metadata={}),
        ContextNode(id="high", text="A" * 3000, score=0.95, metadata={}),
        ContextNode(id="mid", text="C" * 3000, score=0.7, metadata={}),
    ]
    mock_llm_client.complete.return_value = "Answer"

    config = GenerateConfig(max_context_tokens=1000)  # Only room for ~1 context

    # Act
    answer = await rag_engine.generate_answer("test", context, config=config)

    # Assert
    # The prompt should contain the high-score content (A's)
    call_args = mock_llm_client.complete.call_args
    prompt = call_args[0][0]
    assert "A" * 100 in prompt  # High score content included
    # Low score content should NOT be in prompt (truncated)


# =============================================================================
# NEW: Citation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_generate_answer_creates_citations(
    rag_engine, mock_llm_client, mock_context_data
):
    """Test that citations are created from context metadata."""
    # Arrange
    mock_llm_client.complete.return_value = "Answer with sources"

    # Act
    answer = await rag_engine.generate_answer("test", mock_context_data)

    # Assert
    assert len(answer.citations) == 2
    assert all(isinstance(c, Citation) for c in answer.citations)
    # source_id should prefer url > source > id
    assert answer.citations[0].source_id == "http://example.com/doc1"
    assert answer.citations[0].url == "http://example.com/doc1"
    assert answer.citations[0].chunk_id == "1"


@pytest.mark.asyncio
async def test_generate_answer_can_disable_citations(
    rag_engine, mock_llm_client, mock_context_data
):
    """Test that citations can be disabled via config."""
    # Arrange
    mock_llm_client.complete.return_value = "Answer without citations"
    config = GenerateConfig(include_citations=False)

    # Act
    answer = await rag_engine.generate_answer("test", mock_context_data, config=config)

    # Assert
    assert answer.citations == []


# =============================================================================
# NEW: System Prompt Tests
# =============================================================================


@pytest.mark.asyncio
async def test_generate_answer_includes_system_prompt(
    rag_engine, mock_llm_client, mock_context_data
):
    """Test that system prompt is included when provided."""
    # Arrange
    mock_llm_client.complete.return_value = "Formatted answer"
    config = GenerateConfig(system_prompt="You are a helpful assistant. Be concise.")

    # Act
    await rag_engine.generate_answer("test", mock_context_data, config=config)

    # Assert
    call_args = mock_llm_client.complete.call_args
    prompt = call_args[0][0]
    assert "You are a helpful assistant" in prompt


# =============================================================================
# NEW: Persona and Confidence Tests (per docs/02_AGENT_SPECS.md)
# =============================================================================


@pytest.mark.asyncio
async def test_generate_answer_uses_persona_for_tone(
    rag_engine, mock_llm_client, mock_context_data
):
    """Test that persona config is reflected in tone_used field."""
    # Arrange
    mock_llm_client.complete.return_value = "Technical explanation"
    config = GenerateConfig(persona="Technical")

    # Act
    answer = await rag_engine.generate_answer("test", mock_context_data, config=config)

    # Assert
    assert answer.tone_used == "Technical"


@pytest.mark.asyncio
async def test_generate_answer_includes_confidence_score(
    rag_engine, mock_llm_client, mock_context_data
):
    """Test that confidence_score is calculated from context relevance."""
    # Arrange
    mock_llm_client.complete.return_value = "Answer"

    # Act
    answer = await rag_engine.generate_answer("test", mock_context_data)

    # Assert - confidence should be average of scores (0.9 + 0.8) / 2 = 0.85
    assert 0.0 <= answer.confidence_score <= 1.0
    assert answer.confidence_score == pytest.approx(0.85, rel=0.01)


@pytest.mark.asyncio
async def test_generate_answer_low_confidence_with_no_context(
    rag_engine, mock_llm_client
):
    """Test that confidence is low when no context provided."""
    # Arrange
    mock_llm_client.complete.return_value = "I don't know"

    # Act
    answer = await rag_engine.generate_answer("test", [])

    # Assert - confidence should be 0.5 for no context
    assert answer.confidence_score == 0.5


@pytest.mark.asyncio
async def test_answer_has_follow_up_suggestions_field(
    rag_engine, mock_llm_client, mock_context_data
):
    """Test that Answer includes follow_up_suggestions field."""
    # Arrange
    mock_llm_client.complete.return_value = "Answer"

    # Act
    answer = await rag_engine.generate_answer("test", mock_context_data)

    # Assert
    assert hasattr(answer, "follow_up_suggestions")
    assert isinstance(answer.follow_up_suggestions, list)


@pytest.mark.asyncio
async def test_retrieve_populates_source_fields(rag_engine, mock_vector_store):
    """Test that retrieve populates source_id and source_url from metadata."""
    # Arrange
    mock_vector_store.search.return_value = [
        {
            "id": "chunk1",
            "content": "Test content",
            "score": 0.9,
            "metadata": {"source": "doc123", "url": "http://example.com/doc"},
        }
    ]

    # Act
    results = await rag_engine.retrieve("test")

    # Assert
    assert len(results) == 1
    assert results[0].source_id == "doc123"
    assert results[0].source_url == "http://example.com/doc"
