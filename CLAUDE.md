# Claude Code Guidelines - RAG System

## Project Context

You are working on a **Multi-Source Agentic RAG Web Application**. This system uses:
- **ROMA** (Recursive Open Meta-Agent) for query orchestration
- **Dolphin** for layout-aware document parsing
- **LanceDB** for vector storage (NOT ChromaDB)
- **FastAPI** + **Next.js** stack

## Before You Code

1. **Read the docs** in `docs/` folder - they are authoritative (Phase 3 adds `docs/06_FRONTEND_PLAYBOOK.md` for UI/API specifics)
2. **Check schemas** in `src/app/schemas/` - all agent communication uses these
3. **Review tests** in `tests/` - follow TDD, tests define expected behavior

## Key Constraints

### Must Follow
- Use **LanceDB** for vector storage (per `ARCHITECTURE.md`)
- All agent I/O uses **Pydantic schemas** from `src/app/schemas/`
- Return `AgentFailure` on errors with proper error codes
- **Strict typing** - `mypy --strict` must pass
- **88 char line limit** - `ruff` enforces this
- **Async-first** - use `async/await` for I/O
- **Frontend parity** - schema/API changes must be mirrored in `frontend/src/types/` and `frontend/src/lib/api.ts` before landing

### Never Do
- Don't use ChromaDB (project uses LanceDB)
- Don't skip type annotations
- Don't make network calls in unit tests
- Don't create responses without `SourceCitation` (hallucination risk)
- Don't exceed recursion depth of 5 in orchestrator

## Schema Quick Reference

```python
# Error handling - always use AgentFailure
from app.schemas import AgentFailure, ErrorCodes

failure = AgentFailure(
    agent_id="memory",
    error_code=ErrorCodes.MEMORY_NO_RESULTS,
    message="No relevant chunks found",
    recoverable=True
)

# Parser output
from app.schemas import ParserOutput, ParsedChunk

chunk = ParsedChunk(
    chunk_id="chunk_001",
    content="Table content here",
    chunk_index=0,
    layout_type="table"  # "text", "table", "image", "header"
)

# Memory query
from app.schemas import MemoryQuery, MemoryOutput

query = MemoryQuery(
    query_text="What is the budget?",
    top_k=5,
    min_relevance_score=0.7,
    filters={"source_type": "gdrive"}
)

# Tailor output - MUST have citations
from app.schemas import TailorOutput, SourceCitation

citation = SourceCitation(
    source_id="doc_123",
    chunk_id="chunk_001",
    text_snippet="The budget is $45,000",
    url="https://drive.google.com/..."
)
```

## Running Quality Checks

```bash
# Lint and format
ruff check src/ tests/ --fix
ruff format src/ tests/

# Type check
mypy src/

# Run tests
pytest tests/ -v

# All checks (pre-commit)
pre-commit run --all-files

# Frontend checks
(cd frontend && npm run lint && npm run typecheck && npm run test)
```

## Common Patterns

### Adding a new connector
```python
# src/app/connectors/gdrive.py
from app.schemas import ConnectorInput, ConnectorOutput, AgentFailure, ErrorCodes

async def fetch_gdrive_file(input: ConnectorInput) -> ConnectorOutput | AgentFailure:
    try:
        # Implementation
        return ConnectorOutput(
            file_path="/tmp/downloaded.pdf",
            file_size_bytes=1024,
            source_metadata={"author": "user@example.com"},
            checksum="abc123"
        )
    except NotFoundError:
        return AgentFailure(
            agent_id="connector",
            error_code=ErrorCodes.CONNECTOR_NOT_FOUND,
            message="File not found",
            recoverable=False
        )
```

### Writing tests with mocks
```python
# tests/unit/memory/test_memory_agent.py
import pytest
from tests.mocks.mock_vectordb import MockLanceDB
from app.schemas import MemoryQuery

class TestMemoryAgent:
    @pytest.mark.unit
    async def test_query_returns_results(self, populated_vector_db: MockLanceDB):
        query = MemoryQuery(query_text="Python", top_k=3)
        result = await populated_vector_db.query(query)

        assert result.total_found > 0
        assert all(r.relevance_score >= 0.7 for r in result.results)
```

## Frontend Contribution Notes
- Mirror every backend schema you touch inside `frontend/src/types/index.ts` and adjust the API client (`frontend/src/lib/api.ts`) accordingly.
- UI updates live in `frontend/src/app/page.tsx` (ROMA console). Follow the established Tailwind + strict TypeScript patterns (no implicit any, guard nullables).
- Document any new flow or shared component in `docs/06_FRONTEND_PLAYBOOK.md` so other agents/frontend devs know how to interact with it.
- Use `./start.sh` during manual testing to launch both FastAPI (:8000) and Next.js (:3000) simultaneously.

## File Locations

| What | Where |
|------|-------|
| Pydantic schemas | `src/app/schemas/` |
| Error codes | `src/app/schemas/base.py` |
| Test fixtures | `tests/conftest.py` |
| Mock LLM | `tests/mocks/mock_llm.py` |
| Mock VectorDB | `tests/mocks/mock_vectordb.py` |
| Golden dataset | `tests/golden_dataset.json` |
| API types (TS) | `frontend/src/types/index.ts` |

## When Stuck

1. Check `docs/02_AGENT_SPECS.md` for schema definitions
2. Check `docs/04_TEST_PLAN.md` for expected test behavior
3. Look at existing tests in `tests/unit/` for patterns
4. Run `ruff check` and `mypy` to catch issues early
