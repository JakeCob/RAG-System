import pytest
from unittest.mock import MagicMock, AsyncMock
from src.brain.engine import RAGEngine
from src.brain.schemas import ContextNode, Answer, Citation

@pytest.fixture
def mock_vector_store():
    # We use MagicMock for the client itself, but its methods are AsyncMock
    m = MagicMock()
    m.search = AsyncMock()
    return m

@pytest.fixture
def mock_llm_client():
    m = MagicMock()
    m.generate = AsyncMock()
    return m

@pytest.fixture
def rag_engine(mock_vector_store, mock_llm_client):
    return RAGEngine(vector_store=mock_vector_store, llm_client=mock_llm_client)

@pytest.fixture
def mock_context_data():
    return [
        ContextNode(id="1", text="The sky is blue.", score=0.9, metadata={"source": "doc1"}),
        ContextNode(id="2", text="Grass is green.", score=0.8, metadata={"source": "doc2"})
    ]

@pytest.mark.asyncio
async def test_retrieve_calls_vector_store_and_returns_context_nodes(rag_engine, mock_vector_store):
    # Arrange
    query = "What is the color of the sky?"
    mock_vector_store.search.return_value = [
        {"id": "1", "content": "The sky is blue.", "score": 0.9, "metadata": {"source": "doc1"}},
        {"id": "2", "content": "Grass is green.", "score": 0.8, "metadata": {"source": "doc2"}}
    ]

    # Act
    results = await rag_engine.retrieve(query)

    # Assert
    mock_vector_store.search.assert_awaited_once()
    # Check that the call argument was the query (loosely or strictly)
    args, _ = mock_vector_store.search.call_args
    assert query in args[0] or query == args[0]
    
    assert isinstance(results, list)
    assert len(results) == 2
    assert all(isinstance(node, ContextNode) for node in results)
    assert results[0].text == "The sky is blue."
    assert results[0].id == "1"

@pytest.mark.asyncio
async def test_generate_answer_constructs_prompt_with_query_and_context(rag_engine, mock_llm_client, mock_context_data):
    # Arrange
    query = "What colors are mentioned?"
    mock_llm_client.generate.return_value = "Blue and Green."

    # Act
    await rag_engine.generate_answer(query, mock_context_data)

    # Assert
    mock_llm_client.generate.assert_awaited()
    call_args = mock_llm_client.generate.call_args
    # Use repr to convert args/kwargs to string for easy checking
    call_args_str = str(call_args)
    
    assert query in call_args_str
    assert "The sky is blue" in call_args_str
    assert "Grass is green" in call_args_str

@pytest.mark.asyncio
async def test_generate_answer_returns_strict_answer_object(rag_engine, mock_llm_client, mock_context_data):
    # Arrange
    query = "What colors are mentioned?"
    mock_llm_client.generate.return_value = "Blue and Green."

    # Act
    answer = await rag_engine.generate_answer(query, mock_context_data)

    # Assert
    assert isinstance(answer, Answer)
    assert answer.content == "Blue and Green."
    # Ideally it should also parse citations if the LLM returns them, 
    # but for now we check basic structure.
    assert isinstance(answer.citations, list)

@pytest.mark.asyncio
async def test_generate_answer_no_context(rag_engine, mock_llm_client):
    # Arrange
    query = "Unknown topic"
    context = []
    # Mock return value needed for Answer construction even if context is empty
    mock_llm_client.generate.return_value = "I don't know."
    
    # Act
    answer = await rag_engine.generate_answer(query, context)

    # Assert
    assert isinstance(answer, Answer)
    # Should handle gracefully, maybe return "I don't know" or similar.
    # We verify it doesn't crash and returns an Answer.
    assert answer.content