# Ingestion Strategy & Normalization Blueprint

**Role:** Senior Data Engineer & ETL Architect
**Context:** Multi-Source Agentic RAG System (P0-3)
**Reference:** `DESIGN_DOC.md`, `AGENT_SPECS.md`

---

## 1. Executive Summary

This document defines the strict engineering standards for ingesting, normalizing, and chunking data from heterogeneous sources (Local Files, Web, Google Drive) into our unified `ParserOutput` schema. The goal is to ensure that downstream agents (ROMA) receive semantically rich, structure-aware contexts regardless of the data's origin.

## 2. Universal Data Model

All ingestion adapters must ultimately produce a valid `ParserOutput` object.

```python
# Target Schema (from AGENT_SPECS.md)
class ParserOutput(BaseModel):
    document_id: str
    metadata: Dict[str, Any]
    chunks: List[ParsedChunk]
    total_pages: int
    processing_time_ms: float
```

## 3. The "Adapter" Strategy

### 3.1 Local Files (Dolphin Parser)
**Objective:** High-fidelity extraction of PDF/DOCX/PPTX with layout preservation, and fast-path ingestion for plain text.

*   **Tooling:** `DolphinParserService` (with routing logic).
    *   *Complex (PDF/DOCX/PPTX):* Use vision-language models or OCR-layout engines (LayoutPDFReader/Unstructured).
    *   *Simple (.txt/.md):* **Fast-Path.** Direct UTF-8 read.
*   **Layout Preservation Strategy:**
    *   **Plain Text / Markdown (.txt, .md):**
        *   Read file content directly as a string.
        *   Validate/Ensure UTF-8 encoding.
        *   If `.txt`: Treat as a single text block or apply basic heuristic paragraph splitting (double newline).
        *   If `.md`: Validate structure, then pass directly to normalization.
    *   **Complex Documents (PDF/Docs):**
        *   **Text:** Converted to standard Markdown (headers as `#`, lists as `-`).
        *   **Tables:** **CRITICAL.** Tables must *not* be flattened into text. They must be converted to **Markdown Table** format.
        *   *Why?* LLMs understand Markdown tables better than CSV or space-aligned text.
        *   *Implementation:* Detect table bounding box -> Extract cells -> Serialize to `| Col 1 | Col 2 |
|---|---|
`.
    *   **Images:** Extracted, captioned via VLM (Vision Language Model), and inserted as `![Caption](path/to/image)` or embedded separately.

### 3.2 URLs (Web Spider / Crawl4AI)
**Objective:** Noise-free extraction of semantic content from HTML.

*   **Tooling:** `Crawl4AI` (or equivalent headless browser scraper).
*   **Boilerplate Removal Strategy:**
    *   **DOM Traversal:** Target `<main>`, `<article>`, or `div[role="main"]`.
    *   **Negative Selectors:** Aggressively remove `<nav>`, `<footer>`, `<aside>`, `.ad-container`, `.cookie-consent`.
    *   **Heuristics:** Text-to-tag density ratio. If a block has many links but little text, drop it (likely a sidebar).
*   **Markdown Conversion:** Use `html2text` or `trafilatura` specifically tuned to output GitHub-flavored Markdown.

### 3.3 Google Drive (OAuth + Native API)
**Objective:** Secure access and conversion of proprietary Google formats.

*   **Auth Flow:**
    *   **Service Account:** **PREFERRED** for backend/server-side ingestion. Use a shared `credentials.json` with domain-wide delegation if accessing enterprise folders.
    *   **User Token (OAuth2):** Required if acting on behalf of a specific user. Must implement **Token Refresh** logic (see Section 5).
*   **Format Conversion (Proprietary to Markdown):**
    *   **Google Docs:** Use Google Drive API `export` endpoint.
        *   MIME Type: `application/vnd.google-apps.document` -> Export as `text/markdown` (if supported) or `text/html` then convert to Markdown.
    *   **Google Sheets:**
        *   Export as `text/csv`.
        *   Convert CSV to Markdown Table format (limited to reasonable width).
    *   **Google Slides:**
        *   Iterate through slides.
        *   Extract text shapes -> Headers/Bullets.
        *   Extract Speaker Notes -> Append as `> Note: ...`.

---

## 4. The Normalization Pipeline

We employ a "Pipe & Filter" architecture.

**Step 1: Raw Ingestion**
*   Input: `Source Identifier` (Path, URL, ID).
*   Output: `Raw Bytes` + `Native Metadata`.

**Step 2: Cleaning & Sanitization**
*   **Encoding:** Force UTF-8. Fix mojibake.
*   **Whitespace:** Normalize (collapse multiple spaces/newlines).
*   **Security:** Scan for malicious JS (in HTML) or prompt injection patterns (e.g., "Ignore previous instructions").

**Step 3: Universal Markdown Conversion**
*   Transform cleaned data into a single Markdown string.
*   *Invariant:* The output must be human-readable Markdown.

**Step 4: Structural Segmentation (The "Dolphin" Pass)**
*   Parse the Markdown into logical blocks (`ParsedChunk` objects).
*   Identify `layout_type`: "header", "text", "table", "code".

**Step 5: Metadata Tagging & Final Assembly**
*   Construct the `ParserOutput`.
*   Enrich `metadata`: Add `ingest_timestamp`, `source_hash` (for deduplication), `author`, `permissions`.

---

## 5. Chunking Strategy

**Goal:** Maximize semantic retrieval precision in LanceDB.

### Recommended Strategy: Hybrid Semantic-Recursive Splitter

1.  **Level 1: Structure-Aware Splitting (Markdown)**
    *   Use `MarkdownHeaderTextSplitter`.
    *   Split by headers (`#`, `##`, `###`).
    *   *Benefit:* Keeps sections together. A "Pricing" section stays in one chunk.

2.  **Level 2: Recursive Character Splitter (Fallback)**
    *   If a structural chunk > `MAX_TOKEN_LIMIT`, apply `RecursiveCharacterTextSplitter`.
    *   Separators: `

`, `
`, `. `, ` ` (Space).

### Parameters
*   **Vector DB:** LanceDB.
*   **Embedding Model Window:** Assume 8192 tokens (e.g., OpenAI text-embedding-3 or similar).
*   **Chunk Size:** **512 - 1024 tokens**.
    *   *Reasoning:* Large enough to contain full context (a whole table or paragraph), small enough for precise vector matching.
*   **Overlap:** **10% (50-100 tokens)**.
    *   *Reasoning:* Preserves context across split boundaries.

---

## 6. Error Recovery & Resilience

### 6.1 Web Scraper (Crawl4AI) - 403/Rate Limits
*   **Immediate Action:** Catch `HTTP 403/429`.
*   **Strategy:**
    1.  **Rotate User-Agent:** Switch from standard header to a "real user" browser string.
    2.  **Backoff:** Implement exponential backoff (wait 2s, 4s, 8s).
    3.  **Proxy Rotation (Optional):** If implemented, route request through a different IP.
    4.  **Terminal Failure:** Log as `ERR_CONNECTOR_AUTH` and skip URL. Do not crash the pipeline.

### 6.2 GDrive - Token Expiration
*   **Detection:** API call returns `401 Unauthorized`.
*   **Recovery:**
    1.  Check for `refresh_token` in storage.
    2.  Call OAuth endpoint to swap `refresh_token` for new `access_token`.
    3.  Update storage with new tokens.
    4.  **Retry:** Re-execute the failed API call (max 1 retry).
    5.  **Re-auth:** If refresh fails, flag source as `NEEDS_REAUTH` and notify user.

### 6.3 Corrupt/Unreadable Files
*   **Action:** Catch parsing exceptions (e.g., `PDFSyntaxError`).
*   **Fallback:** Attempt basic text extraction (ignoring layout).
*   **Reporting:** Return `AgentFailure` object (as defined in `AGENT_SPECS.md`) with `recoverable=False`.

## 7. Phase 3 Frontend Hook

The Next.js ROMA console pipes file uploads directly into `POST /ingest`:

1. The operator selects a document + Bearer token in `frontend/src/app/page.tsx`.
2. The file is streamed via `frontend/src/lib/api.ts` using `FormData` with strict error handling.
3. FastAPI validates the token (`settings.ingest_auth_token`) before calling `IngestionService.ingest_document`.
4. The UI surfaces the returned `task_id`, `filename`, and `status` to confirm the job queue.

> Keep this contract stable—QA relies on it for manual ingestion smoke tests, and TypeScript mirrors live in `frontend/src/types/index.ts`.
