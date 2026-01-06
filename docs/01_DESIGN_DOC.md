<executive_summary>

### Problem Statement
Enterprise knowledge is currently fragmented across siloed repositories (Google Drive, Intranets, Local Filesystems), making retrieval inefficient and context-poor. Traditional RAG systems fail to understand complex document layouts (tables, charts) or adapt to the user's technical proficiency, leading to "flat" and often irrelevant answers.

### "AI-Force-Multiplier" Value Proposition
This Agentic RAG system acts as an intelligent force multiplier by combining **Dolphin’s** vision-aware parsing with **ROMA’s** recursive orchestration. Unlike standard search, it "sees" document structure and "thinks" about the query plan. By bridging raw data with agentic reasoning via **LanceDB** and **GenAI Toolbox**, we transform static retrieval into dynamic, persona-aware knowledge synthesis, reducing time-to-insight by an estimated 40%.

</executive_summary>

<system_architecture>

### 1. Data Flow Pipeline (Ingestion & Indexing)
1.  **Ingestion Layer**: Connectors for GDrive (Oauth2), Web Scraper (URLs), and Local File Watchers.
2.  **Parsing Layer (Dolphin)**:
    *   Raw files (PDF, PPTX, HTML) are sent to the `DolphinParserService`.
    *   Dolphin performs OCR and layout analysis to distinguish headers, body text, and tabular data.
    *   Output is normalized into semantic Markdown blocks.
3.  **Embedding & Storage**:
    *   Markdown blocks are chunked (sliding window).
    *   Vector embeddings generated via high-dimensional model.
    *   Metadata and Vectors stored in **LanceDB** for fast, persistent retrieval.

### 2. Multi-Agent Orchestration (ROMA)
1.  **User Request**: "Explain the Q3 impact on our cloud budget."
2.  **ROMA Planner**: Decomposes request -> ["Retrieve Q3 Cloud Reports (GDrive)", "Fetch Pricing Page (URL)", "Compare values"].
3.  **Recursive Execution**:
    *   *Atomizer Node*: Dispatches sub-tasks to specific agents.
    *   *Retrieval Agents*: Query LanceDB via GenAI Toolbox.
    *   *Verifier Node*: Cross-references Executor outputs with source chunks to ensure strict grounding.
4.  **Synthesis & Finalization**:
    *   *Synthesizer*: Aggregates validated data, resolving conflicts (prioritizing timestamp/authority).
    *   *Reviewer/Persona Adapter*: Final polish for tone, formatting, and safety before delivery.

</system_architecture>

<frontend_experience>

### 3. Frontend Experience (Phase 3)
1. **ROMA Console (Next.js 14)**:
    *   Landing page located at `frontend/src/app/page.tsx`.
    *   Provides persona selector, free-form query input, and a grounded answer panel that renders Tailor citations numerically.
    *   Includes an ingestion card so operators can upload files alongside a Bearer token that maps to the FastAPI `/ingest` auth guard.
2. **Shared Contracts**:
    *   TypeScript interfaces in `frontend/src/types/index.ts` are generated to mirror every Pydantic schema (`AgentFailure`, `TailorOutput`, `QueryRequest`, SSE envelopes, etc.).
    *   Any backend schema change must propagate here plus to the API client before release.
3. **API Client**:
    *   `frontend/src/lib/api.ts` provides deterministic helpers for `/health`, `/query` (sync + SSE), and `/ingest`.
    *   Converts backend `AgentFailure` payloads into user-visible alerts and streams `StreamEvent` tokens for future progressive rendering.
4. **Lifecycle**:
    *   The top-level `start.sh` script launches both FastAPI (`uvicorn app.api:app --app-dir src`) and Next.js (`npm run dev`) so designers and QA can exercise the full ROMA loop locally.

</frontend_experience>

<subsystem_definitions>

### DolphinParserService
*   **Responsibility**: Converts unstructured, visually complex documents into machine-readable structure.
*   **Key Behavior**:
    *   Detects and serializes tables into Markdown/CSV string representations to preserve semantic relationships during embedding.
    *   Extracts embedded images for separate multi-modal indexing.
    *   **Input**: `Blob` (PDF/Image)
    *   **Output**: `StructuredDocument` (List of Sections with metadata).

### ROMAOrchestrator
*   **Responsibility**: Manages the lifecycle of the agentic mesh using a recursive loop.
*   **Roles**:
    *   **Planner**: Breaks down complex queries into a DAG (Directed Acyclic Graph) of tasks.
    *   **Executor**: Interfaces with the GenAI Toolbox to execute tool calls (Search, Calc, Read).
    *   **Verifier**: A strict "Grounding Check" agent that validates every claim against retrieved `SourceCitation`s. Rejects unsubstantiated claims.
    *   **Synthesizer**: Merges multi-source outputs, resolving data conflicts (e.g., URL vs. GDrive) via authority heuristics, and ensures narrative flow.
    *   **Reviewer**: The final gatekeeper. Checks for tone alignment, formatting, and safety violations before releasing the `TailoredResponse`.

</subsystem_definitions>

<data_schema>

```python
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl

class SourceCitation(BaseModel):
    source_id: str = Field(..., description="Unique identifier for the document source")
    url: Optional[HttpUrl] = Field(None, description="Direct link if web-based or GDrive link")
    chunk_text: str = Field(..., description="The exact text snippet used for grounding")
    relevance_score: float = Field(..., description="Cosine similarity score from LanceDB")

class TailoredResponse(BaseModel):
    content: str = Field(..., description="The synthesized answer text")
    tone: Literal["Technical", "Executive", "General"] = Field(
        ..., description="Detected user persona driving the output style"
    )
    citations: List[SourceCitation] = Field(default_factory=list)
    follow_up_suggestions: List[str] = Field(
        default_factory=list, description="Suggested next questions based on context"
    )
```

</data_schema>

<non_functional_requirements>

1.  **Latency**:
    *   Vector Retrieval (LanceDB): < 100ms (p95).
    *   End-to-End Query Response: < 2s for "Cached/Simple" queries; < 10s for "Deep Research" mode.
2.  **Reliability**:
    *   **GDrive Ingestion**: Must implement exponential backoff and jitter for API rate limits (429 errors).
    *   **Fault Tolerance**: Agent loops must have a maximum recursion depth (e.g., n=5) to prevent infinite loops.
3.  **Hallucination & Safety**:
    *   All claims in `TailoredResponse` must have a corresponding `SourceCitation`.
    *   The *Reviewer* agent acts as a semantic guardrail, rejecting answers with low evidence scores.

</non_functional_requirements>

<known_unknowns>

1.  **Dolphin Parsing Latency**: Processing extremely large PDFs (100+ pages) with heavy visual content might introduce unacceptable ingestion lag. Need to benchmark async batching.
2.  **Conflict Resolution Heuristics**: When GDrive docs and Public URLs contradict each other, determining the "Source of Truth" programmatically is complex. We need to define strict authority weighting rules.
3.  **Prompt Injection in Ingested Content**: Malicious instructions embedded in scraped URLs could theoretically hijack the ROMA agents. Input sanitization at the Dolphin layer is a critical TBD.

</known_unknowns>
