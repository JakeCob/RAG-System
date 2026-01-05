# AI Agent Guidelines - Tests

## Testing Philosophy

This project follows **TDD (Test-Driven Development)** with a "Red-Green-Refactor" workflow:
1. Write failing tests first
2. Implement code to pass tests
3. Refactor while keeping tests green

Reference: `docs/04_TEST_PLAN.md`

## Directory Structure

```
tests/
├── api/              # Backend API contract tests (Section 4)
├── integration/      # End-to-end smoke tests (Section 7)
├── mocks/            # Mock implementations (Section 2)
│   ├── mock_llm.py       # MockLLMClient
│   └── mock_vectordb.py  # MockLanceDB
├── unit/             # Per-agent unit tests (Section 3)
│   ├── chunking/         # TestChunkingStrategy
│   ├── connector/        # TestConnectorAgent
│   ├── guardrails/       # TestGuardrailsAgent
│   ├── memory/           # TestMemoryAgent
│   ├── orchestrator/     # TestROMAOrchestrator
│   ├── parser/           # TestDolphinParser
│   ├── state/            # TestConversationState
│   └── tailor/           # TestTailorAgent
├── conftest.py       # Shared fixtures
└── golden_dataset.json  # Regression test data
```

## Key Fixtures (from `conftest.py`)

```python
# LLM Mocks
mock_llm                  # Fresh MockLLMClient
mock_llm_with_responses   # Pre-configured responses

# Vector DB Mocks
mock_vector_db            # Fresh MockLanceDB
populated_vector_db       # Pre-seeded with test data

# External Service Mocks
mock_gdrive_service       # GDrive API responses
mock_crawler_responses    # Web scraper responses

# Configuration
test_config               # Standard test parameters
sample_embedding          # Sample vector for tests
```

## Test Class Naming

Each agent has a corresponding test class:

| Agent | Test Class | File |
|-------|-----------|------|
| Parser | `TestDolphinParser` | `unit/parser/test_dolphin_parser.py` |
| Guardrails | `TestGuardrailsAgent` | `unit/guardrails/test_guardrails_agent.py` |
| Memory | `TestMemoryAgent` | `unit/memory/test_memory_agent.py` |
| Tailor | `TestTailorAgent` | `unit/tailor/test_tailor_agent.py` |
| Connector | `TestConnectorAgent` | `unit/connector/test_connector_agent.py` |
| Chunking | `TestChunkingStrategy` | `unit/chunking/test_chunking_strategy.py` |
| Orchestrator | `TestROMAOrchestrator` | `unit/orchestrator/test_roma_orchestrator.py` |
| State | `TestConversationState` | `unit/state/test_conversation_state.py` |

## Test Markers

```python
@pytest.mark.unit          # Fast, isolated tests
@pytest.mark.integration   # May require services
@pytest.mark.slow          # Long-running tests
```

## Rules

1. **No network calls** in unit tests - use mocks
2. **Use fixtures** from `conftest.py` for external deps
3. **Test both success and failure paths**
4. **Assert on schema compliance** - outputs must match Pydantic models
5. **80% coverage minimum**

## Golden Dataset

`tests/golden_dataset.json` contains regression test cases:

```json
{
  "id": 1,
  "question": "What is the Q3 cloud budget?",
  "ground_truth_key_phrase": ["$45,000", "45k"],
  "retrieval_target_source_id": "gdrive_finance_q3.pdf"
}
```

Use for:
- RAG accuracy testing
- Retrieval benchmarking (Hit Rate @ K, MRR)
- LLM comparison testing
