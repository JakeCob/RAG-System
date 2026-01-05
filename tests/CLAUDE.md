# Claude Guidelines - Tests

## Quick Start

```python
import pytest
from app.schemas import MemoryQuery, AgentFailure, ErrorCodes
from tests.mocks.mock_vectordb import MockLanceDB

class TestMemoryAgent:
    @pytest.mark.unit
    async def test_query_with_results(self, populated_vector_db: MockLanceDB):
        query = MemoryQuery(query_text="Python programming", top_k=3)
        result = await populated_vector_db.query(query)

        assert result.total_found > 0
        assert all(r.relevance_score >= 0.7 for r in result.results)

    @pytest.mark.unit
    async def test_query_no_results(self, mock_vector_db: MockLanceDB):
        query = MemoryQuery(query_text="nonexistent topic", top_k=3)
        result = await mock_vector_db.query(query)

        assert result.total_found == 0
```

## Available Fixtures

### From `conftest.py`

```python
# Use in test function signature
def test_something(
    mock_llm,                  # MockLLMClient - fresh instance
    mock_llm_with_responses,   # MockLLMClient - has preset responses
    mock_vector_db,            # MockLanceDB - empty
    populated_vector_db,       # MockLanceDB - has 3 sample docs
    mock_gdrive_service,       # Dict with GDrive mock responses
    mock_crawler_responses,    # Dict with web crawler mock responses
    test_config,               # Dict with standard config values
    sample_embedding,          # list[float] - sample vector
):
    pass
```

### Mock Objects

```python
# MockLLMClient (tests/mocks/mock_llm.py)
mock_llm = MockLLMClient(responses={"pattern": "response"})
response = await mock_llm.complete("prompt with pattern")
assert mock_llm.call_history  # Track calls for assertions

# MockLanceDB (tests/mocks/mock_vectordb.py)
db = MockLanceDB()
await db.add_documents(
    documents=["text1", "text2"],
    embeddings=[[0.1, 0.2], [0.3, 0.4]],
    metadata=[{"source": "a"}, {"source": "b"}],
    source_ids=["doc1", "doc2"]
)
result = await db.query(MemoryQuery(query_text="test", top_k=2))
```

## Test Patterns

### Testing schema validation
```python
def test_schema_validation():
    from app.schemas import ParsedChunk

    # Valid chunk
    chunk = ParsedChunk(
        chunk_id="c1",
        content="Hello",
        chunk_index=0,
        layout_type="text"
    )
    assert chunk.layout_type == "text"

    # Invalid layout_type should raise
    with pytest.raises(ValidationError):
        ParsedChunk(
            chunk_id="c1",
            content="Hello",
            chunk_index=0,
            layout_type="invalid"  # Not in Literal
        )
```

### Testing error handling
```python
@pytest.mark.unit
async def test_returns_agent_failure_on_error():
    # Arrange
    input_data = ConnectorInput(
        source_type="local",
        source_identifier="/nonexistent/path.pdf"
    )

    # Act
    result = await connector.fetch(input_data)

    # Assert
    assert isinstance(result, AgentFailure)
    assert result.error_code == ErrorCodes.CONNECTOR_NOT_FOUND
    assert result.recoverable is False
```

### Testing async functions
```python
@pytest.mark.unit
async def test_async_operation():
    # pytest-asyncio handles the event loop
    result = await some_async_function()
    assert result is not None
```

## Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Specific test class
pytest tests/unit/memory/test_memory_agent.py::TestMemoryAgent -v

# With coverage
pytest tests/ --cov=src/app --cov-report=html

# Skip slow tests
pytest tests/ -v -m "not slow"
```

## Test File Template

```python
"""Agent Name tests.

Reference: docs/04_TEST_PLAN.md Section X.X
Test Class: TestAgentName
"""

import pytest

from app.schemas import InputSchema, OutputSchema, AgentFailure, ErrorCodes


class TestAgentName:
    """Tests for the Agent ("The Role")."""

    @pytest.mark.unit
    async def test_success_case(self, fixture_name):
        """Description of what success looks like."""
        # Arrange
        input_data = InputSchema(...)

        # Act
        result = await agent.process(input_data)

        # Assert
        assert isinstance(result, OutputSchema)
        assert result.some_field == expected_value

    @pytest.mark.unit
    async def test_failure_case(self, fixture_name):
        """Description of failure scenario."""
        # Arrange
        bad_input = InputSchema(...)

        # Act
        result = await agent.process(bad_input)

        # Assert
        assert isinstance(result, AgentFailure)
        assert result.error_code == ErrorCodes.EXPECTED_ERROR
```

## Common Assertions

```python
# Schema type checking
assert isinstance(result, TailorOutput)

# List contents
assert len(result.citations) > 0
assert all(isinstance(c, SourceCitation) for c in result.citations)

# Score thresholds
assert all(r.relevance_score >= 0.7 for r in results)

# Error codes
assert result.error_code == ErrorCodes.MEMORY_NO_RESULTS

# Call tracking (mocks)
assert len(mock_llm.call_history) == 1
assert "expected_prompt" in mock_llm.call_history[0]["prompt"]
```
