# Phase 4 Plan: Production Readiness & Feature Expansion

**Role:** Lead Technical Program Manager & Architect
**Phase:** 4 (Production Hardening)
**Prerequisites:** Phase 3 Complete (Backend/Frontend Integration, Tests Passing, Type Safety)
**Date:** 2026-01-06

---

## Executive Summary

**Phase 4 Theme:** Production Readiness & Core Feature Expansion

Phase 3 delivered a working ROMA console with backend integration, strict typing, and foundational tests. Phase 4 focuses on making the system production-ready by:
1. **Connecting Real LLMs** (replacing mocks with OpenAI/Anthropic)
2. **Hardening Operations** (auth, monitoring, error handling)
3. **Expanding Ingestion** (GDrive, Web, multi-format support)
4. **Enhancing UX** (streaming, progressive rendering, advanced citations)
5. **Achieving Coverage** (>80% test coverage, golden dataset validation)

---

## Phase 4 Exit Criteria

### Quality Gates
- [ ] All unit tests passing (`pytest tests/unit/ -v`)
- [ ] All integration tests passing (`pytest tests/integration/ -v`)
- [ ] Backend API tests passing (`pytest tests/api/ -v`)
- [ ] Frontend tests passing (`cd frontend && npm run test`)
- [ ] Lint/format clean (backend: `ruff check && ruff format --check`, frontend: `npm run lint`)
- [ ] Type checking passing (backend: `mypy src/`, frontend: `npm run typecheck`)
- [ ] Test coverage ≥80% (measured via `pytest --cov=src/app`)

### Feature Completeness
- [ ] Real LLM integration (OpenAI/Anthropic) operational
- [ ] GDrive OAuth ingestion functional
- [ ] Web scraping with Crawl4AI operational
- [ ] Multi-format parsing (PDF/DOCX/PPTX/TXT/MD/HTML)
- [ ] Streaming query responses with progressive rendering
- [ ] Golden dataset validation passing (≥85% accuracy)
- [ ] Citation rendering with source links functional

### Operational Readiness
- [ ] Structured logging with log levels (INFO/WARN/ERROR)
- [ ] Health check endpoint comprehensive (DB + LLM + agents)
- [ ] Auth middleware functional (Bearer tokens for `/ingest`)
- [ ] Error handling standardized (all agents return `AgentFailure` on errors)
- [ ] Rate limiting implemented for LLM calls
- [ ] Graceful degradation when LLM/DB unavailable

---

## Phase 4 Task Breakdown

### **P4-1: Real LLM Integration (Orchestrator & Tailor)**
**Goal:** Replace mock LLMs with OpenAI/Anthropic APIs for production query execution.

**Scope:**
- Implement `LLMService` abstraction (`src/app/services/llm.py`)
  - Support for OpenAI (`gpt-4o`, `gpt-4o-mini`)
  - Support for Anthropic (`claude-sonnet-3.5`, `claude-opus-3`)
  - Configurable via environment variables (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`)
- Update `ROMAOrchestrator` to use `LLMService` for planning
- Update `TailorAgent` to use `LLMService` for synthesis
- Add retry logic with exponential backoff (handle 429/503 errors)
- Add token counting and cost tracking (log tokens/request)
- Write unit tests for `LLMService` (mock HTTP responses)
- Write integration test: end-to-end query with real LLM (marked `@pytest.mark.integration`)

**Dependencies:** None (foundational)

**Artifacts:**
- `src/app/services/llm.py`
- `tests/unit/services/test_llm_service.py`
- `tests/integration/test_llm_integration.py`
- Updated `settings.py` with LLM config

**Tests:**
- `test_llm_service_openai_success`
- `test_llm_service_anthropic_success`
- `test_llm_service_rate_limit_retry`
- `test_llm_service_invalid_api_key`
- `test_end_to_end_query_with_real_llm` (integration, requires API key)

---

### **P4-2: GDrive Connector Implementation**
**Goal:** Enable secure ingestion from Google Drive with OAuth2 authentication.

**Scope:**
- Implement `GDriveConnector` (`src/app/connectors/gdrive.py`)
  - OAuth2 flow (Service Account preferred, User Token fallback)
  - Token refresh logic (handle 401 errors)
  - File download with streaming (handle large files)
  - Exponential backoff for rate limits (429 errors)
  - Support for native Google formats (Docs/Sheets/Slides → Markdown/CSV)
- Add GDrive credentials configuration (`settings.py`)
- Write unit tests with mocked `googleapiclient`
- Write integration test with test GDrive folder (manual setup required)
- Update `IngestionService` to route GDrive sources to `GDriveConnector`

**Dependencies:** None

**Artifacts:**
- `src/app/connectors/gdrive.py`
- `tests/unit/connector/test_gdrive_connector.py`
- `tests/integration/test_gdrive_ingestion.py` (requires test credentials)
- `docs/08_GDRIVE_SETUP.md` (setup guide for OAuth)

**Tests:**
- `test_gdrive_list_files`
- `test_gdrive_download_file`
- `test_gdrive_token_refresh`
- `test_gdrive_rate_limit_backoff`
- `test_gdrive_export_native_formats` (Docs → Markdown)
- `test_gdrive_auth_failure` (401 → `ERR_CONNECTOR_AUTH`)

---

### **P4-3: Web Connector with Crawl4AI**
**Goal:** Enable web scraping with boilerplate removal and sanitization.

**Scope:**
- Implement `WebConnector` (`src/app/connectors/web.py`)
  - Integration with Crawl4AI or equivalent (e.g., `beautifulsoup4` + `trafilatura`)
  - Boilerplate removal (nav/footer/ads)
  - HTML → Markdown conversion
  - User-Agent rotation (handle 403/429)
  - Content sanitization (strip `<script>`, detect malicious payloads)
- Add web scraping config (`settings.py`: timeouts, max depth, allowed domains)
- Write unit tests with mock HTML responses
- Write integration test with real web pages (use archive.org for stability)
- Update `IngestionService` to route web URLs to `WebConnector`

**Dependencies:** None

**Artifacts:**
- `src/app/connectors/web.py`
- `tests/unit/connector/test_web_connector.py`
- `tests/integration/test_web_ingestion.py`
- `docs/09_WEB_SCRAPING.md` (best practices, ethical considerations)

**Tests:**
- `test_web_fetch_success`
- `test_web_boilerplate_removal`
- `test_web_html_to_markdown`
- `test_web_user_agent_rotation`
- `test_web_sanitization` (detect `<script>` injection)
- `test_web_403_backoff`

---

### **P4-4: Multi-Format Parser Expansion**
**Goal:** Extend Dolphin parser to handle PDF, DOCX, PPTX, XLSX, EPUB with layout preservation.

**Scope:**
- Extend `DolphinParserService` (`src/app/parsers/dolphin.py`)
  - **PDF:** OCR + layout detection (tables, headers, images) using `unstructured` or `pdfplumber`
  - **DOCX:** Extract text/tables with `python-docx`
  - **PPTX:** Extract slides/speaker notes with `python-pptx`
  - **XLSX/CSV:** Convert to Markdown tables with `pandas`
  - **EPUB:** Extract chapters with `ebooklib`
- Implement table serialization (tables → Markdown format)
- Implement image extraction + captioning (optional: use VLM for alt text)
- Write unit tests for each format (use fixtures from `tests/fixtures/`)
- Write integration test: ingest multi-format folder → query

**Dependencies:** None

**Artifacts:**
- Updated `src/app/parsers/dolphin.py`
- `tests/unit/parser/test_dolphin_pdf.py`
- `tests/unit/parser/test_dolphin_docx.py`
- `tests/unit/parser/test_dolphin_pptx.py`
- `tests/unit/parser/test_dolphin_xlsx.py`
- `tests/fixtures/` (sample files for testing)

**Tests:**
- `test_parse_pdf_with_tables`
- `test_parse_docx_headers_and_lists`
- `test_parse_pptx_slides_and_notes`
- `test_parse_xlsx_to_markdown_table`
- `test_parse_epub_chapters`
- `test_parse_malformed_pdf` (expect `AgentFailure`)

---

### **P4-5: Streaming Query with Progressive Rendering**
**Goal:** Implement Server-Sent Events (SSE) for streaming ROMA responses to frontend.

**Scope:**
- Extend `ROMAOrchestrator.stream_query()` to yield `StreamEvent` objects
  - Emit `token` events for incremental text generation
  - Emit `complete` event with final `TailorOutput`
  - Emit `error` event on failure with `AgentFailure`
- Update FastAPI `/query` endpoint to handle `stream=True` parameter
- Update frontend API client (`frontend/src/lib/api.ts`)
  - Implement SSE parsing with `EventSource` or `fetch` + streaming
  - Render tokens progressively in ROMA console
- Add loading states (spinner → streaming → complete)
- Write unit tests for SSE event generation
- Write E2E test (Playwright/Cypress): submit query → observe streaming

**Dependencies:** P4-1 (LLM integration required for streaming)

**Artifacts:**
- Updated `src/app/agents/orchestrator.py`
- Updated `src/app/api/__init__.py` (`_stream_sse()`)
- Updated `frontend/src/lib/api.ts` (`streamQuery()`)
- Updated `frontend/src/app/page.tsx` (progressive rendering UI)
- `tests/api/test_streaming.py`

**Tests:**
- `test_stream_query_emits_tokens`
- `test_stream_query_emits_complete`
- `test_stream_query_emits_error_on_failure`
- `test_frontend_renders_streaming_tokens` (E2E)

---

### **P4-6: Golden Dataset Validation**
**Goal:** Establish regression testing with golden dataset (Section 6.2 of TEST_PLAN.md).

**Scope:**
- Create `tests/golden_dataset.json` with 10+ query/answer pairs
  - Cover multiple sources (GDrive, Web, Local)
  - Cover multiple personas (Technical, Executive, General)
  - Cover edge cases (no results, multi-hop reasoning, conflicting sources)
- Implement `tests/regression/test_golden_dataset.py`
  - Load dataset → run queries → compare responses
  - Use LLM-as-a-judge for answer quality (GPT-4o grades responses 1-5)
  - Assert ≥85% queries pass (match ground truth)
- Automate golden dataset tests in CI pipeline
- Document dataset format in `docs/04_TEST_PLAN.md`

**Dependencies:** P4-1, P4-2, P4-3, P4-4 (requires full ingestion + LLM)

**Artifacts:**
- `tests/golden_dataset.json`
- `tests/regression/test_golden_dataset.py`
- `.github/workflows/regression.yml` (CI integration)

**Tests:**
- `test_golden_dataset_accuracy` (assert ≥85% pass rate)
- `test_golden_dataset_citation_coverage` (all answers have citations)

---

### **P4-7: Observability & Monitoring**
**Goal:** Implement structured logging, metrics, and health checks for production ops.

**Scope:**
- Implement structured logging (`src/app/utils/logging.py`)
  - Use `structlog` or Python `logging.config`
  - Log levels: DEBUG, INFO, WARN, ERROR
  - Include request IDs, agent IDs, timestamps
  - Redact PII (SSN, API keys) in logs
- Extend `/health` endpoint
  - Check LanceDB connectivity
  - Check LLM API reachability
  - Check agent initialization status
  - Return degraded/offline status codes
- Add metrics instrumentation (optional: Prometheus)
  - Query latency (P50/P95/P99)
  - LLM token usage
  - Error rates by agent
- Document logging patterns in `docs/10_OBSERVABILITY.md`

**Dependencies:** P4-1 (LLM health check)

**Artifacts:**
- `src/app/utils/logging.py`
- Updated `src/app/api/__init__.py` (enhanced `/health`)
- `docs/10_OBSERVABILITY.md`
- `tests/api/test_health_check.py`

**Tests:**
- `test_health_check_all_connected`
- `test_health_check_db_offline`
- `test_health_check_llm_unreachable`
- `test_structured_logging_includes_request_id`
- `test_logging_redacts_pii`

---

### **P4-8: Error Handling Hardening**
**Goal:** Ensure all agents return standardized `AgentFailure` and orchestrator handles graceful degradation.

**Scope:**
- Audit all agents for error handling compliance
  - Memory, Tailor, Guardrails, Connector, Parser
  - All exceptions → `AgentFailure` with proper error codes
- Implement orchestrator error recovery
  - Retry transient failures (timeouts, rate limits)
  - Skip non-recoverable failures (auth errors, unsupported formats)
  - Fallback to degraded responses (e.g., "I don't know" if memory fails)
- Add error handling tests (one per agent)
- Document error codes in `docs/02_AGENT_SPECS.md`

**Dependencies:** None (refactoring existing code)

**Artifacts:**
- Updated agent implementations (`src/app/agents/*.py`, `src/app/connectors/*.py`)
- Updated `docs/02_AGENT_SPECS.md` (error code table)
- `tests/unit/orchestrator/test_error_recovery.py`

**Tests:**
- `test_orchestrator_retries_timeout`
- `test_orchestrator_skips_auth_failure`
- `test_orchestrator_fallback_on_memory_failure`
- `test_all_agents_return_agent_failure_on_error` (meta-test)

---

### **P4-9: Frontend UX Enhancements**
**Goal:** Improve ROMA console with citations, follow-ups, error alerts, and loading states.

**Scope:**
- **Citations Rendering:**
  - Display numeric badges `[1]`, `[2]` next to cited text
  - Show expandable citation list with source URLs
  - Implement click-to-source navigation
- **Follow-up Suggestions:**
  - Render suggested questions as clickable pills
  - Click pill → auto-populate query input
- **Error Alerts:**
  - Render `AgentFailure` as toast/alert with error code + message
  - Distinguish recoverable vs. non-recoverable errors
- **Loading States:**
  - Show spinner during query execution
  - Show streaming indicator during progressive rendering
- Write component tests (React Testing Library)
- Write E2E tests (Playwright)

**Dependencies:** P4-5 (streaming), P4-1 (real LLM)

**Artifacts:**
- Updated `frontend/src/app/page.tsx`
- New `frontend/src/components/CitationList.tsx`
- New `frontend/src/components/ErrorAlert.tsx`
- `frontend/src/test/page.test.tsx`
- E2E tests in `frontend/e2e/` (Playwright)

**Tests:**
- `test_citation_badges_rendered`
- `test_citation_click_opens_source`
- `test_follow_up_pill_populates_input`
- `test_agent_failure_renders_alert`
- `test_loading_spinner_during_query` (E2E)

---

### **P4-10: Test Coverage & Documentation**
**Goal:** Achieve ≥80% test coverage and comprehensive documentation for Phase 4 features.

**Scope:**
- Run coverage analysis: `pytest --cov=src/app --cov-report=html`
- Identify untested code paths (focus on error handling, edge cases)
- Write missing unit tests to reach 80% coverage
- Update documentation:
  - `docs/02_AGENT_SPECS.md` (new error codes)
  - `docs/03_INGESTION_STRATEGY.md` (GDrive/Web connectors)
  - `docs/04_TEST_PLAN.md` (golden dataset, streaming tests)
  - `docs/06_FRONTEND_PLAYBOOK.md` (new UI components)
- Generate API documentation (consider FastAPI `/docs` + Swagger)

**Dependencies:** P4-1 through P4-9 (all features implemented)

**Artifacts:**
- Coverage report (`htmlcov/index.html`)
- Updated documentation files
- API documentation (`/docs` endpoint)

**Tests:**
- `test_coverage_exceeds_80_percent` (meta-test)

---

## Phase 4 Task Dependencies (DAG)

```
P4-1 (LLM Integration)  ──┬──> P4-5 (Streaming)  ──┬──> P4-9 (Frontend UX)
                          │                        │
P4-2 (GDrive Connector) ──┤                        │
                          ├──> P4-6 (Golden Dataset) ──> P4-10 (Coverage & Docs)
P4-3 (Web Connector) ─────┤                        │
                          │                        │
P4-4 (Parser Expansion) ──┘                        │
                                                    │
P4-7 (Observability) ──────────────────────────────┘
                                                    │
P4-8 (Error Hardening) ────────────────────────────┘
```

**Critical Path:** P4-1 → P4-5 → P4-6 → P4-10
**Parallelizable:** P4-2, P4-3, P4-4 (can run concurrently)
**Infrastructure:** P4-7, P4-8 (can start early, continue throughout)

---

## Forward-Looking Roadmap (Phases 5+)

### **Phase 5: Advanced RAG & Multi-Modal**
**Theme:** Enhanced Retrieval & Multi-Modal Support
**Duration:** ~2-3 weeks
**Key Objectives:**
1. **Hybrid Search:** Combine vector search (LanceDB) with keyword search (BM25/Elasticsearch)
2. **Re-ranking:** Implement cross-encoder re-ranking for improved precision
3. **Multi-Modal Embeddings:** Index images with CLIP, enable visual search
4. **Conversation Memory:** Implement session persistence (Redis/PostgreSQL)
5. **Query Decomposition:** Advanced multi-hop reasoning with DAG execution
6. **Citation Verification:** Automated fact-checking with source cross-referencing

**Exit Criteria:**
- Hybrid search operational (vector + keyword)
- Image search functional (query images by description)
- Multi-turn conversations with context preservation
- Re-ranking improves MRR by ≥15%

---

### **Phase 6: Enterprise Features & Security**
**Theme:** Multi-Tenancy, Auth, and Compliance
**Duration:** ~2-3 weeks
**Key Objectives:**
1. **Multi-Tenancy:** Isolate data by organization/user
2. **Role-Based Access Control (RBAC):** Permissions for docs/queries
3. **SSO Integration:** SAML/OAuth for enterprise login
4. **Audit Logging:** Track all queries, ingestions, accesses
5. **PII Detection:** Automated redaction (SSN, credit cards, emails)
6. **Data Retention Policies:** Automated cleanup of old data

**Exit Criteria:**
- Multi-tenant deployment operational
- RBAC enforced (users can only access permitted docs)
- SSO login functional
- Audit logs queryable (who accessed what, when)

---

### **Phase 7: Scalability & Performance**
**Theme:** Horizontal Scaling & Optimization
**Duration:** ~2-3 weeks
**Key Objectives:**
1. **Async Processing:** Background ingestion queues (Celery/RQ)
2. **Caching:** Redis cache for frequent queries
3. **Load Balancing:** Deploy behind Nginx/K8s with multiple replicas
4. **Vector DB Sharding:** Partition LanceDB for massive datasets (>1M docs)
5. **LLM Response Caching:** Cache LLM responses for duplicate queries
6. **Cost Optimization:** Dynamic model selection (GPT-4o vs. GPT-4o-mini)

**Exit Criteria:**
- System handles 1000 concurrent users
- P95 query latency <3s (cached) and <10s (uncached)
- Ingestion throughput >100 docs/min
- LLM costs reduced by 40% via caching + smart routing

---

### **Phase 8: Advanced UX & Analytics**
**Theme:** User Experience & Intelligence
**Duration:** ~2 weeks
**Key Objectives:**
1. **Conversational UI:** Chat interface with message history
2. **Query Suggestions:** Auto-complete, related queries
3. **Visual Analytics:** Dashboard for query trends, popular topics
4. **User Feedback Loop:** Thumbs up/down on responses
5. **A/B Testing:** Test multiple LLMs/prompts, measure quality
6. **Export Functionality:** Export answers as PDF/DOCX with citations

**Exit Criteria:**
- Chat interface deployed (multi-turn conversations)
- Analytics dashboard operational
- User feedback captured and analyzed
- A/B testing framework operational

---

## Phase 4 Success Metrics

### Quantitative
- **Test Coverage:** ≥80% (measured via `pytest --cov`)
- **Golden Dataset Accuracy:** ≥85% (10+ queries pass ground truth validation)
- **Query Latency:** P95 <10s end-to-end (with real LLM)
- **Ingestion Throughput:** ≥10 docs/min (local/GDrive/web)
- **Error Rate:** <5% (queries resulting in unhandled exceptions)

### Qualitative
- All Phase 4 tasks (P4-1 through P4-10) completed
- All quality gates passing (tests, lint, type, coverage)
- Documentation updated and comprehensive
- System deployable to staging environment (manual smoke test passes)
- Product Owner/Stakeholder sign-off on ROMA console UX

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM API rate limits | High | High | Implement aggressive retry + exponential backoff + fallback models |
| GDrive OAuth complexity | Medium | Medium | Use Service Account for MVP; defer User OAuth to Phase 6 |
| Dolphin parsing latency | Medium | High | Async ingestion queues (defer to Phase 7); optimize chunking strategy |
| Test coverage gaps | Medium | Medium | Continuous monitoring with `pytest --cov`; block PRs <80% |
| Frontend-backend schema drift | Low | High | Enforce schema parity tests; automate TypeScript generation from Pydantic |
| LLM cost overruns | Medium | Medium | Implement token budgets; use cheaper models for simple queries |

---

## Communication Plan

### Daily Standups
- What did you complete yesterday?
- What are you working on today?
- Any blockers?

### Weekly Sprint Review
- Demo completed tasks (P4-1, P4-2, etc.)
- Review golden dataset results
- Update roadmap based on findings

### Stakeholder Updates
- Share test coverage reports
- Demo ROMA console with streaming
- Review cost projections for LLM usage

---

## Conclusion

Phase 4 transforms the RAG system from a working prototype into a production-ready application. By completing P4-1 through P4-10, we will have:
- Real LLM integration for query execution
- Multi-source ingestion (GDrive, Web, Local)
- Multi-format parsing (PDF, DOCX, PPTX, etc.)
- Streaming UX with progressive rendering
- Comprehensive test coverage (≥80%)
- Golden dataset validation (≥85% accuracy)
- Operational readiness (logging, monitoring, error handling)

This sets the foundation for Phases 5-8, which will add advanced RAG techniques, enterprise features, scalability, and analytics.

**Phase 4 is the bridge from MVP to Production.**
