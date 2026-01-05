# AI Agent Guidelines - Backend (src/app)

## Module Overview

This is the **FastAPI backend** implementing the RAG pipeline agents.

## Directory Structure

```
src/app/
├── agents/        # ROMA Orchestrator, Tailor Agent
├── api/           # FastAPI routes (/query, /ingest, /health)
├── config/        # pydantic-settings for environment config
├── connectors/    # Data source connectors (GDrive, Web, Local)
├── guardrails/    # Input/output safety and PII filtering
├── memory/        # LanceDB vector store operations
├── parser/        # Dolphin document parsing
└── schemas/       # Pydantic models (AUTHORITATIVE SOURCE)
```

## Agent Implementation Pattern

Each agent follows this pattern:

```python
from app.schemas import AgentInput, AgentOutput, AgentFailure, ErrorCodes

async def process(input: AgentInput) -> AgentOutput | AgentFailure:
    """
    Process input and return output or failure.

    Args:
        input: Validated Pydantic input model

    Returns:
        AgentOutput on success, AgentFailure on error
    """
    try:
        # Implementation
        return AgentOutput(...)
    except SpecificError as e:
        return AgentFailure(
            agent_id="agent_name",
            error_code=ErrorCodes.SPECIFIC_ERROR,
            message=str(e),
            recoverable=True
        )
```

## Schema Usage

**All agent I/O MUST use schemas from `schemas/`**

| Agent | Input Schema | Output Schema |
|-------|-------------|---------------|
| Guardrails | `GuardrailsInput` | `GuardrailsOutput` |
| Connector | `ConnectorInput` | `ConnectorOutput` |
| Parser | `ParserInput` | `ParserOutput` |
| Memory | `MemoryQuery` | `MemoryOutput` |
| Tailor | `TailorInput` | `TailorOutput` |
| Orchestrator | `OrchestratorInput` | `OrchestratorOutput` |

## Key Files

- `schemas/base.py` - Error codes, type aliases
- `schemas/__init__.py` - All exports (import from here)
- `config/` - Use `pydantic-settings` for env vars

## Dependencies

- **LanceDB** for vector storage
- **sentence-transformers** for embeddings
- **unstructured** for document parsing
- **httpx** for async HTTP
- **openai** for LLM calls

## Coding Standards

- Async functions for all I/O
- Type hints on all functions
- Docstrings with Args/Returns
- Max complexity: 10 (McCabe)
- Line length: 88 chars
