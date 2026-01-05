# Agent Contracts & Subsystem Specification

## 1. Agent Role Definitions

### Guardrails Agent (Security / Sentinel)
**Responsibility:** "The Shield."
Ensures safety and security for both incoming user requests and outgoing agent responses. It acts as the gatekeeper against prompt injection, malicious payloads, and PII leakage.
*   **Primary Task:** `UserRequest` -> `SafeRequest` AND `AgentResponse` -> `SafeResponse`.
*   **Key Behavior:** Must detect prompt injection attempts and redact sensitive information (PII) before it reaches the orchestration layer.

### Connector Agent (Ingestion / Fetcher)
**Responsibility:** "The Hand."
Interfaces with external data sources (GDrive, Web, APIs, Local FS) to retrieve raw content. It handles authentication, crawling, rate-limiting, and downloading files to a local temporary workspace.
*   **Primary Task:** `SourceURL/ID` -> `LocalFilePath`.
*   **Key Behavior:** Handles authentication (OAuth), retries (exponential backoff), and ensures files are successfully downloaded before passing control to the Parser.

### Parser Agent (Ingestion / Dolphin)
**Responsibility:** "The Eyes."
Ingests raw documents (PDF, HTML, DOCX, PPTX) and converts them into semantically rich, structured data. It must handle OCR, layout detection (tables vs. text), and chunking.
*   **Primary Task:** Convert `Blob` -> `List[StructuredChunk]`.
*   **Key Behavior:** Must detect tables and serialize them as Markdown/CSV to preserve structure.

### Memory Agent (Retrieval / LanceDB Interface)
**Responsibility:** "The Librarian."
Manages the Vector Store (LanceDB). It handles embedding generation (if not pre-computed), semantic search, and metadata filtering.
*   **Primary Task:** `Query` -> `List[RelevantChunk]`.
*   **Key Behavior:** Returns context with strict relevance scores and source tracking.

### Tailor Agent (Synthesis / Reviewer)
**Responsibility:** "The Editor."
Synthesizes the final response from retrieved context. It applies persona (tone), ensures grounding (citations), and formats the output (e.g., Markdown, JSON).
*   **Primary Task:** `Query + Context` -> `FinalResponse`.
*   **Key Behavior:** Strict hallucination check. If context is insufficient, it must state that explicitly rather than guessing.

### Orchestrator (ROMA Router)
**Responsibility:** "The Brain."
Manages the request lifecycle. It analyzes the user intent, decomposes complex queries into sub-tasks (e.g., "retrieve X", "retrieve Y", "compare"), dispatches to other agents, and manages the conversation state.
*   **Primary Task:** `UserRequest` -> `Plan` -> `Execution` -> `Response`.

---

## 2. Pydantic-Style Schema Definitions

All agents must adhere to these schemas for inter-process communication.

```python
from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

# --- Shared Models ---

class AgentMetadata(BaseModel):
    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model_version: str

# --- 0. Guardrails Agent Schemas ---

class GuardrailsInput(BaseModel):
    content: str
    check_type: Literal["input_validation", "output_safety"]
    metadata: Optional[Dict[str, Any]] = None

class GuardrailsOutput(BaseModel):
    is_safe: bool
    sanitized_content: str
    risk_category: Optional[Literal["injection", "pii", "hate_speech", "malicious_code", "none"]]
    reasoning: str

# --- 1. Connector Agent Schemas ---

class ConnectorInput(BaseModel):
    source_type: Literal["gdrive", "web", "local"]
    source_identifier: str = Field(..., description="URL, File Path, or GDrive File ID")
    credentials_id: Optional[str] = None
    recursive: bool = False

class ConnectorOutput(BaseModel):
    file_path: str = Field(..., description="Local absolute path to the downloaded file")
    file_size_bytes: int
    source_metadata: Dict[str, Any] = Field(..., description="Original metadata (e.g., GDrive author, URL headers)")
    checksum: str

# --- 2. Parser Agent Schemas ---

class ParserInput(BaseModel):
    file_path: str = Field(..., description="Local path or temp URL to the file")
    file_type: Literal["pdf", "html", "docx", "pptx", "txt"]
    ingestion_source: Literal["gdrive", "local", "web_scrape"]
    force_ocr: bool = False

class ParsedChunk(BaseModel):
    chunk_id: str
    content: str = Field(..., description="The text content or serialized table markdown")
    chunk_index: int
    page_number: Optional[int]
    layout_type: Literal["text", "table", "image", "header"]
    bbox: Optional[List[float]] = Field(None, description="[x1, y1, x2, y2] coordinates if applicable")

class ParserOutput(BaseModel):
    document_id: str
    metadata: Dict[str, Any]
    chunks: List[ParsedChunk]
    total_pages: int
    processing_time_ms: float

# --- 3. Memory Agent Schemas ---

class MemoryQuery(BaseModel):
    query_text: str
    top_k: int = 5
    min_relevance_score: float = 0.7
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters (e.g., source_type='gdrive')")

class RetrievedContext(BaseModel):
    chunk_id: str
    content: str
    source_id: str
    source_url: Optional[str]
    relevance_score: float
    metadata: Dict[str, Any]

class MemoryOutput(BaseModel):
    results: List[RetrievedContext]
    total_found: int

# --- 4. Tailor Agent Schemas ---

class TailorInput(BaseModel):
    user_query: str
    context_chunks: List[RetrievedContext]
    persona: Literal["Technical", "Executive", "General"] = "General"
    formatting_instructions: Optional[str] = None

class SourceCitation(BaseModel):
    source_id: str
    chunk_id: str
    text_snippet: str
    url: Optional[str]

class TailorOutput(BaseModel):
    content: str = Field(..., description="The synthesized response")
    citations: List[SourceCitation]
    tone_used: str
    follow_up_suggestions: List[str]
    confidence_score: float

# --- 5. Orchestrator Schemas ---

class PlanStep(BaseModel):
    step_id: int
    description: str
    tool_call: str
    status: Literal["pending", "in_progress", "completed", "failed"]

class OrchestratorInput(BaseModel):
    user_message: str
    session_id: str
    user_id: str

class OrchestratorOutput(BaseModel):
    final_response: TailorOutput
    execution_plan: List[PlanStep]
    processing_time_total_ms: float
```

---

## 3. State Management Protocol

State is passed as a serializable JSON object (or Pydantic model) called `ConversationState`. This is maintained by the Orchestrator and passed *by reference* or *value* depending on the implementation (likely passed as a context object to agent functions).

### Structure

```python
class ConversationMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime

class ConversationState(BaseModel):
    session_id: str
    history: List[ConversationMessage] = []
    
    # The "Short-term Memory" / Working Context for the current turn
    current_plan: Optional[List[PlanStep]] = None
    accumulated_context: List[RetrievedContext] = []
    
    # Metadata for the session
    user_preferences: Dict[str, Any] = {}
    
    def add_message(self, role: str, content: str):
        self.history.append(ConversationMessage(role=role, content=content, timestamp=datetime.utcnow()))
        
    def clear_context(self):
        self.accumulated_context = []
        self.current_plan = None
```

### Protocol
1.  **Initiation:** Orchestrator creates/loads `ConversationState` based on `session_id`.
2.  **Pass-through:** 
    *   Orchestrator calls **Memory Agent** -> Updates `accumulated_context`.
    *   Orchestrator calls **Tailor Agent** -> Reads `accumulated_context` and `history`.
3.  **Persistence:** State is persisted to Redis/Database at the end of each turn.

---

## 4. Error Handling Schemas

All agents must return a standardized error object if they fail, allowing the Orchestrator to decide whether to retry, fallback, or fail gracefully.

### AgentFailure Schema

```python
class AgentFailure(BaseModel):
    agent_id: str
    error_code: str
    message: str
    recoverable: bool = False
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### Standard Error Codes

| Code | Meaning | Expected Orchestrator Action |
| :--- | :--- | :--- |
| `ERR_GUARDRAIL_INJECTION` | Prompt injection detected | Block request, warn user |
| `ERR_GUARDRAIL_UNSAFE` | Output contains unsafe content/PII | Block response, retry with stricter instructions |
| `ERR_CONNECTOR_AUTH` | Authentication failed (401/403) | Request new credentials or skip |
| `ERR_CONNECTOR_NOT_FOUND` | Source not found (404) | Notify user, skip source |
| `ERR_PARSER_ENCRYPTED` | File is password protected | Ask user for password or skip |
| `ERR_PARSER_UNSUPPORTED` | File type not supported | Notify user, skip file |
| `ERR_MEMORY_NO_RESULTS` | No embeddings found > threshold | Broaden search or ask clarifying question |
| `ERR_TAILOR_HALLUCINATION` | Verification failed (no citations) | Retry with strict instruction or fallback to "I don't know" |
| `ERR_TIMEOUT` | Agent took too long | Retry once, then fail |
