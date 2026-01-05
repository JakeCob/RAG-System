# Claude Guidelines - Backend (src/app)

## Quick Start

```python
# Always import schemas from the package root
from app.schemas import (
    ConnectorInput, ConnectorOutput,
    ParserInput, ParserOutput, ParsedChunk,
    MemoryQuery, MemoryOutput, RetrievedContext,
    TailorInput, TailorOutput, SourceCitation,
    AgentFailure, ErrorCodes,
)
```

## Module Responsibilities

### `guardrails/`
- Detect prompt injection in user input
- Redact PII from responses
- Block toxic/harmful content
- Return `GuardrailsOutput` with `is_safe` and `risk_category`

### `connectors/`
- Fetch files from GDrive (OAuth), Web (scraping), Local FS
- Handle auth, retries, rate limiting
- Return `ConnectorOutput` with `file_path` and `checksum`
- Use exponential backoff for 429/403 errors

### `parser/`
- Convert PDF/DOCX/PPTX/HTML to structured chunks
- Preserve table structure as Markdown tables (CRITICAL)
- Detect layout types: "text", "table", "image", "header"
- Return `ParserOutput` with `ParsedChunk` list

### `memory/`
- Interface with LanceDB (NOT ChromaDB)
- Generate embeddings with sentence-transformers
- Return `MemoryOutput` with `RetrievedContext` list
- Support metadata filtering

### `agents/`
- **Orchestrator**: Plan → Execute → Verify loop (max depth: 5)
- **Tailor**: Synthesize response with citations
- Manage `ConversationState` for session context

### `api/`
- `POST /query` - Query the RAG system
- `POST /ingest` - Upload and process documents
- `GET /health` - Health check endpoint

## Common Patterns

### Async database operations
```python
async def query_vectors(query: MemoryQuery) -> MemoryOutput:
    # LanceDB operations
    results = await db.search(query.query_text).limit(query.top_k).execute()
    return MemoryOutput(results=[...], total_found=len(results))
```

### Error handling
```python
from app.schemas import AgentFailure, ErrorCodes

# Return failure, don't raise
if not results:
    return AgentFailure(
        agent_id="memory",
        error_code=ErrorCodes.MEMORY_NO_RESULTS,
        message=f"No results above threshold {query.min_relevance_score}",
        recoverable=True,
        details={"query": query.query_text}
    )
```

### Configuration
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    lancedb_path: str = "./data/lancedb"
    chunk_size: int = 512
    chunk_overlap: int = 50

    class Config:
        env_file = ".env"
```

## Type Aliases (from `schemas/base.py`)

```python
SourceType = Literal["gdrive", "web", "local"]
IngestionSource = Literal["gdrive", "local", "web_scrape"]
FileType = Literal["pdf", "html", "docx", "pptx", "txt", "md"]
LayoutType = Literal["text", "table", "image", "header"]
Persona = Literal["Technical", "Executive", "General"]
```

## Verification Commands

```bash
# From project root
ruff check src/app/
mypy src/app/
pytest tests/unit/ -v
```
