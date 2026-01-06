# Sprint Backlog: Multi-Source Agentic RAG

## [CORE-01] Implement Shared Pydantic Schema Library

**Priority:** P0
**Assignee:** Gemini
**Description:**
Create the foundational library containing all Pydantic models and shared types defined in `AGENT_SPECS.md`. This library will serve as the contract for inter-agent communication, ensuring strict typing and validation across the Connector, Parser, Memory, and Orchestrator services.

**Technical Requirements:**
*   Implement all schemas from `AGENT_SPECS.md` Section 2:
    *   **Common:** `AgentMetadata`, `AgentFailure` (Section 4).
    *   **Guardrails:** `GuardrailsInput`, `GuardrailsOutput`.
    *   **Connector:** `ConnectorInput`, `ConnectorOutput`.
    *   **Parser:** `ParserInput`, `ParsedChunk`, `ParserOutput`.
    *   **Memory:** `MemoryQuery`, `RetrievedContext`, `MemoryOutput`.
    *   **Tailor:** `TailorInput`, `TailorOutput`, `SourceCitation`.
    *   **Orchestrator:** `PlanStep`, `OrchestratorInput`, `OrchestratorOutput`, `ConversationState` (Section 3).
*   Ensure all models support JSON serialization.

**Acceptance Criteria:**
- [ ] All Pydantic models are implemented in a shared module (e.g., `src/models.py`).
- [ ] `AgentFailure` schema includes the `recoverable` boolean field.
- [ ] Unit tests verify that a `ParserOutput` object correctly validates nested `ParsedChunk` lists.
- [ ] `ConversationState` correctly handles the `history` list management.

**Dependencies:**
*   Independent (Blocker for all other tickets).

---

## [INGEST-01] Build Connector Agent with Local File Watcher

**Priority:** P0
**Assignee:** Codex
**Description:**
Implement the `Connector Agent` responsible for fetching raw files. For this sprint, focus on the **Local File Watcher** and a mock interface for GDrive/Web to ensure the pipeline functions without external API dependencies.

**Technical Requirements:**
*   Implement `ConnectorInput` and `ConnectorOutput` schemas.
*   **Local Source:** Implement logic to read files from a watched directory, generating a file hash for deduplication.
*   **Mock Sources:** Implement "Stub" connectors for `gdrive` and `web` that return pre-defined content for testing (per `TEST_PLAN.md` Section 2.1 & 2.2).
*   **Error Handling:** Return `AgentFailure` with code `ERR_CONNECTOR_NOT_FOUND` if a file path is invalid.

**Acceptance Criteria:**
- [ ] `ConnectorAgent` accepts a local file path and returns a valid `ConnectorOutput`.
- [ ] `ConnectorOutput` contains the correct `file_size_bytes` and `checksum`.
- [ ] Unit test `test_local_file_ingestion` passes (file addition triggers processing).
- [ ] Unit test `test_retry_logic_backoff` passes (mocked failure triggers retry).

**Dependencies:**
*   CORE-01

---

## [INGEST-02] Implement Dolphin Parser Service (Markdown Normalization)

**Priority:** P1
**Assignee:** Claude
**Description:**
Develop the `DolphinParserService` to convert raw files into structure-aware Markdown chunks. This agent acts as the "Eyes" of the system, preserving document layout (headers, tables) during ingestion.

**Technical Requirements:**
*   Adhere to `INGESTION_STRATEGY.md` Section 3 ("The Adapter Strategy").
*   **Text/MD:** "Fast-Path" direct read.
*   **PDF/Docs:** Use a library (e.g., `unstructured` or `pypdf`) to extract text.
*   **Table Logic:** **CRITICAL:** Detect tables and serialize them into Markdown Table format (`| Col | Col |`), *not* flat text.
*   **Chunking:** Implement the "Hybrid Semantic-Recursive Splitter" (Section 5):
    1.  `MarkdownHeaderTextSplitter` (Level 1).
    2.  `RecursiveCharacterTextSplitter` (Level 2) with 512-1024 token size and 10% overlap.

**Acceptance Criteria:**
- [ ] Inputting a Markdown file with headers results in chunks split by those headers.
- [ ] Inputting a file with a table results in a `ParsedChunk` with `layout_type="table"`.
- [ ] Unit test `test_chunk_size_limits` passes (no chunk > 1024 tokens).
- [ ] Unit test `test_parse_malformed_pdf` returns `AgentFailure`.

**Dependencies:**
*   CORE-01

---

## [MEM-01] Memory Agent with LanceDB Integration

**Priority:** P0
**Assignee:** Gemini
**Description:**
Implement the `Memory Agent` ("The Librarian") to handle vector storage and semantic retrieval using LanceDB. This agent bridges the parsed data and the reasoning agents.

**Technical Requirements:**
*   Implement `MemoryQuery` and `MemoryOutput` interfaces.
*   **Storage:** Use LanceDB (embedded) to store `ParsedChunk` objects.
*   **Embedding:** Use a standard model (e.g., `sentence-transformers` or OpenAI API) to generate vectors.
*   **Retrieval:** Implement vector search with cosine similarity and support for `metadata` filtering (e.g., `source_type`).

**Acceptance Criteria:**
- [ ] `add_documents` successfully inserts vectors into LanceDB.
- [ ] `query` returns relevant chunks with `relevance_score` > `min_relevance_score`.
- [ ] Unit test `test_exact_match_retrieval` passes (known text is retrieved with high score).
- [ ] Unit test `test_retrieve_no_results` returns `AgentFailure` with `ERR_MEMORY_NO_RESULTS`.

**Dependencies:**
*   CORE-01, INGEST-02

---

## [AGENT-01] ROMA Orchestrator (Recursive Planning Loop)

**Priority:** P1
**Assignee:** Claude
**Description:**
Build the `ROMAOrchestrator` ("The Brain") that manages the recursive "Plan -> Execute -> Verify" loop. It breaks down user requests into actionable steps and delegates to other agents.

**Technical Requirements:**
*   Implement `OrchestratorInput` and `OrchestratorOutput`.
*   **State Management:** Manage `ConversationState` (history, current plan).
*   **Planner Node:** Use an LLM to generate a DAG of `PlanStep`s based on the user query.
*   **Recursive Loop:** Implement the execution loop with a maximum recursion depth (e.g., n=5) to prevent infinite cycles.
*   **Routing:** Dispatch steps to `MemoryAgent` (Retrieval) or `TailorAgent` (Synthesis).

**Acceptance Criteria:**
- [ ] Orchestrator accepts a query and generates a `PlanStep` list.
- [ ] System handles multi-step plans (e.g., "Retrieve X" -> "Synthesize").
- [ ] Recursion depth limit is enforced (test `test_max_recursion_depth`).
- [ ] State is correctly updated after each step.

**Dependencies:**
*   CORE-01, MEM-01

---

## [AGENT-02] Tailor Agent (Grounded Synthesis & Persona)

**Priority:** P1
**Assignee:** Codex
**Description:**
Implement the `Tailor Agent` ("The Editor") responsible for generating the final response. It must strictly ground all claims in the provided context and adopt the requested persona.

**Technical Requirements:**
*   Implement `TailorInput` and `TailorOutput`.
*   **Grounding:** Ensure every claim has a corresponding `SourceCitation`. If context is missing, return "I don't know" or `AgentFailure` (`ERR_TAILOR_HALLUCINATION`).
*   **Persona:** Modify output tone based on `persona` field ("Technical", "Executive", "General").
*   **Formatting:** Return clean Markdown with embedded citations.

**Acceptance Criteria:**
- [ ] Response includes valid `SourceCitation` objects linked to the text.
- [ ] "Technical" persona produces detailed, jargon-appropriate output.
- [ ] Unit test `test_hallucination_handling` passes (asking about missing info triggers fallback).
- [ ] Unit test `test_citation_format` verifies citation structure.

**Dependencies:**
*   CORE-01, MEM-01

---

## [API-01] FastAPI Gateway & End-to-End Integration

**Priority:** P0
**Assignee:** Gemini
**Description:**
Construct the FastAPI backend that exposes the Multi-Agent system to the frontend. This ticket integrates all previous components into a cohesive application.

**Technical Requirements:**
*   **Endpoints:**
    *   `POST /query`: Accepts user text, triggers ROMA Orchestrator, returns `TailoredResponse`.
    *   `POST /ingest`: Accepts file upload, triggers Connector -> Parser -> Memory pipeline.
    *   `GET /health`: Returns system status.
*   **Middleware:** Implement basic error handling to catch `AgentFailure` exceptions and return appropriate HTTP codes (e.g., 400 for Bad Request, 500 for Internal Error).

**Acceptance Criteria:**
- [ ] Server starts and `/health` returns 200 OK.
- [ ] `POST /ingest` successfully processes a uploaded PDF and stores it in LanceDB.
- [ ] `POST /query` returns a grounded answer derived from the ingested PDF.
- [ ] Integration test `test_end_to_end` passes (full flow verification).

**Dependencies:**
*   All Previous Tickets (CORE-01, INGEST-01/02, MEM-01, AGENT-01/02)

---

## [P3-06] Frontend Integration & Shared Contracts

**Priority:** P0  
**Assignee:** Frontend Guild  
**Description:** Deliver a minimal-yet-functional ROMA console that consumes the FastAPI contracts, mirrors backend schemas, and exposes ingestion/query capabilities with grounding/citation UX.

**Technical Requirements:**
*   Mirror every schema from `src/app/schemas/api.py`, `memory.py`, `tailor.py`, and `base.py` inside `frontend/src/types/index.ts`.
*   Implement a typed API client (`frontend/src/lib/api.ts`) that wraps `/health`, `/query` (sync & SSE), and `/ingest` with deterministic `AgentFailure` handling.
*   Build the Next.js 14 App Router experience (`frontend/src/app/page.tsx`) featuring:
    *   Persona selector + query textarea with validation and loading states.
    *   Grounded answer card that renders Tailor content, tone, confidence, follow-up suggestions, and numbered citations.
    *   Ingestion form (file upload + Bearer token) surfacing `IngestResponse` details.
*   Ensure `npm run lint`, `npm run typecheck`, and `npm run test` pass alongside backend quality gates.

**Acceptance Criteria:**
- [x] `/health` badges render on load; failures show fallback copy.
- [x] Query submission returns Tailor output with citations and AgentFailure errors when guardrails trip.
- [x] Ingestion form rejects missing file/token and displays queued task metadata on success.
- [x] Docs updated: README, AGENTS, CLAUDE, `docs/01-06`, plus new `docs/06_FRONTEND_PLAYBOOK.md`.

**Dependencies:** API-01
