# AI Agent Guidelines - RAG System

## Project Overview

This is a **Multi-Source Agentic RAG (Retrieval-Augmented Generation) Web Application** implementing:
- **ROMA** (Recursive Open Meta-Agent) for orchestration
- **Dolphin** for layout-aware document parsing
- **LanceDB** for vector storage
- **FastAPI** backend + **Next.js** frontend

## Critical Documentation

Before making changes, read these docs in order:
1. `docs/01_DESIGN_DOC.md` - System architecture and data flow
2. `docs/02_AGENT_SPECS.md` - Agent contracts and Pydantic schemas (AUTHORITATIVE)
3. `docs/03_INGESTION_STRATEGY.md` - Document parsing and chunking strategy
4. `docs/04_TEST_PLAN.md` - TDD strategy and test requirements

## Architecture

```
User Request → Guardrails → Orchestrator (ROMA) → Memory Agent → Tailor → Response
                                ↓
              Connector → Parser (Dolphin) → LanceDB
```

### Agent Roles
| Agent | Role | Module |
|-------|------|--------|
| Guardrails | "The Shield" - Security/PII filtering | `src/app/guardrails/` |
| Connector | "The Hand" - Data source fetching | `src/app/connectors/` |
| Parser | "The Eyes" - Document parsing (Dolphin) | `src/app/parser/` |
| Memory | "The Librarian" - Vector storage/retrieval | `src/app/memory/` |
| Tailor | "The Editor" - Response synthesis | `src/app/agents/` |
| Orchestrator | "The Brain" - ROMA coordination | `src/app/agents/` |

## Code Standards

### Python (Backend)
- **Python 3.11+** required
- **Strict typing**: All functions must have type annotations
- **Pydantic v2**: All inter-agent communication uses schemas from `src/app/schemas/`
- **Async-first**: Use `async/await` for I/O operations
- **Linting**: `ruff` (strict) + `mypy` (strict mode)

### TypeScript (Frontend)
- **Next.js 14** with App Router
- **Strict TypeScript**: `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`
- **Tailwind CSS** for styling

## Schema Compliance

All agents MUST use schemas from `src/app/schemas/`. Key schemas:
- `AgentFailure` - Standardized error handling with error codes
- `ParserOutput` / `ParsedChunk` - Document parsing results
- `MemoryQuery` / `RetrievedContext` - Vector search interface
- `TailorOutput` / `SourceCitation` - Response with grounding
- `ConversationState` - Session state management

## Error Handling

Use standardized error codes from `src/app/schemas/base.py`:
- `ERR_GUARDRAIL_INJECTION` - Prompt injection detected
- `ERR_CONNECTOR_NOT_FOUND` - Source not found (404)
- `ERR_PARSER_UNSUPPORTED` - Unsupported file type
- `ERR_MEMORY_NO_RESULTS` - No relevant chunks found
- `ERR_TAILOR_HALLUCINATION` - Response not grounded in context

## Testing Requirements

- **TDD approach**: Write tests before implementation
- **Mocking**: Use fixtures from `tests/conftest.py` for external deps
- **No network calls** in unit tests
- **80% coverage** minimum
- Test files mirror the structure in `docs/04_TEST_PLAN.md`

## File Organization

```
src/app/
├── agents/        # ROMA Orchestrator, Tailor Agent
├── api/           # FastAPI routes
├── config/        # pydantic-settings configuration
├── connectors/    # GDrive, Web, Local file connectors
├── guardrails/    # Input/output safety checks
├── memory/        # LanceDB vector store interface
├── parser/        # Dolphin document parser
└── schemas/       # Pydantic models (AUTHORITATIVE)

tests/
├── api/           # Backend API contract tests
├── integration/   # End-to-end tests
├── mocks/         # MockLLM, MockLanceDB
└── unit/          # Per-agent unit tests

frontend/
└── src/
    ├── app/       # Next.js pages
    ├── components/# React components
    ├── lib/       # Utils, API client
    └── types/     # TypeScript interfaces
```

## Common Tasks

### Adding a new agent
1. Create module in `src/app/{agent_name}/`
2. Add schemas to `src/app/schemas/{agent_name}.py`
3. Export from `src/app/schemas/__init__.py`
4. Create test file in `tests/unit/{agent_name}/`
5. Add mock to `tests/mocks/` if needed

### Adding a new API endpoint
1. Add route in `src/app/api/`
2. Create test in `tests/api/test_backend_api.py`
3. Update frontend types in `frontend/src/types/`
4. Add API client method in `frontend/src/lib/api.ts`

### Modifying schemas
1. Update `src/app/schemas/*.py`
2. Run `ruff check src/ && mypy src/`
3. Update corresponding tests
4. Update frontend types if API-facing
