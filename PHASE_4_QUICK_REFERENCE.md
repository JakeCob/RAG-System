# Phase 4 Quick Reference

**Full Plan:** See `docs/07_PHASE_4_PLAN.md` for comprehensive details.

---

## Phase 4 Theme
**Production Readiness & Core Feature Expansion**

---

## 10 Core Tasks (At a Glance)

| Task | Name | Dependencies | Key Outcome |
|------|------|--------------|-------------|
| **P4-1** | Real LLM Integration | None | OpenAI/Anthropic APIs operational |
| **P4-2** | GDrive Connector | None | OAuth2-based GDrive ingestion |
| **P4-3** | Web Connector | None | Web scraping with Crawl4AI |
| **P4-4** | Parser Expansion | None | PDF/DOCX/PPTX/XLSX/EPUB support |
| **P4-5** | Streaming Queries | P4-1 | SSE-based progressive rendering |
| **P4-6** | Golden Dataset | P4-1,2,3,4 | ≥85% accuracy on regression tests |
| **P4-7** | Observability | P4-1 | Logging, monitoring, health checks |
| **P4-8** | Error Hardening | None | Standardized AgentFailure handling |
| **P4-9** | Frontend UX | P4-5 | Citations, streaming UI, alerts |
| **P4-10** | Coverage & Docs | All | ≥80% test coverage, complete docs |

---

## Critical Path
```
P4-1 → P4-5 → P4-6 → P4-10
```

## Parallelizable (Start Immediately)
- P4-2 (GDrive)
- P4-3 (Web)
- P4-4 (Parser)

## Infrastructure (Continuous)
- P4-7 (Observability)
- P4-8 (Error Handling)

---

## Exit Criteria (Quick Checklist)

### Tests & Quality
- [ ] All tests passing (unit/integration/API/frontend)
- [ ] Coverage ≥80%
- [ ] Lint/format clean
- [ ] Type checking passing

### Features
- [ ] Real LLM operational
- [ ] Multi-source ingestion (GDrive/Web/Local)
- [ ] Multi-format parsing (6+ formats)
- [ ] Streaming queries functional
- [ ] Golden dataset ≥85% accuracy

### Operations
- [ ] Structured logging
- [ ] Comprehensive health checks
- [ ] Auth middleware
- [ ] Graceful error handling

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Test Coverage | ≥80% |
| Golden Dataset Accuracy | ≥85% |
| Query Latency (P95) | <10s |
| Ingestion Throughput | ≥10 docs/min |
| Error Rate | <5% |

---

## Future Phases (High-Level)

- **Phase 5:** Advanced RAG (hybrid search, re-ranking, multi-modal)
- **Phase 6:** Enterprise (multi-tenancy, RBAC, SSO)
- **Phase 7:** Scalability (async queues, caching, sharding)
- **Phase 8:** UX & Analytics (chat UI, dashboards, A/B testing)

---

## Next Immediate Actions

1. ✅ Review `docs/07_PHASE_4_PLAN.md`
2. ⚙️ Set up LLM API keys (OpenAI/Anthropic)
3. ⚙️ Configure GDrive credentials (Service Account)
4. 🚀 Start P4-1 (LLM Integration)
5. 🚀 Launch P4-2, P4-3, P4-4 in parallel

---

## Key Files to Update

### Backend
- `src/app/services/llm.py` (P4-1)
- `src/app/connectors/gdrive.py` (P4-2)
- `src/app/connectors/web.py` (P4-3)
- `src/app/parsers/dolphin.py` (P4-4)
- `src/app/agents/orchestrator.py` (P4-5)
- `src/app/utils/logging.py` (P4-7)

### Frontend
- `frontend/src/lib/api.ts` (P4-5)
- `frontend/src/app/page.tsx` (P4-9)
- `frontend/src/components/CitationList.tsx` (P4-9)
- `frontend/src/components/ErrorAlert.tsx` (P4-9)

### Tests
- `tests/unit/services/test_llm_service.py` (P4-1)
- `tests/unit/connector/test_gdrive_connector.py` (P4-2)
- `tests/unit/connector/test_web_connector.py` (P4-3)
- `tests/regression/test_golden_dataset.py` (P4-6)
- `tests/golden_dataset.json` (P4-6)

### Docs
- `docs/08_GDRIVE_SETUP.md` (P4-2)
- `docs/09_WEB_SCRAPING.md` (P4-3)
- `docs/10_OBSERVABILITY.md` (P4-7)

---

## Risk Mitigation Summary

| Risk | Mitigation |
|------|------------|
| 🚨 LLM rate limits | Retry logic + fallback models |
| 🚨 GDrive OAuth complexity | Service Account (simpler than User OAuth) |
| 🚨 Parsing latency | Async queues + optimized chunking |
| 🚨 Test coverage gaps | Continuous monitoring + PR blocking |
| 🚨 Schema drift | Automated TypeScript generation |
| 🚨 Cost overruns | Token budgets + smart routing |

---

## Commands Reference

### Backend
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=src/app --cov-report=html

# Lint and format
ruff check src/ tests/ --fix
ruff format src/ tests/

# Type check
mypy src/

# Start backend
./start.sh  # or: uvicorn app.api:app --app-dir src --reload
```

### Frontend
```bash
cd frontend

# Install deps
npm install

# Lint & type check
npm run lint
npm run typecheck

# Run tests
npm run test

# Start dev server
npm run dev

# E2E tests
npx playwright test
```

---

## Communication Cadence

- **Daily Standups:** Task progress, blockers
- **Weekly Reviews:** Demo completed features, update roadmap
- **Milestone Reports:** Coverage reports, golden dataset results, cost projections

---

## Definition of Done (Per Task)

- [ ] Implementation complete
- [ ] Unit tests written and passing
- [ ] Integration tests written (if applicable)
- [ ] Lint/format clean
- [ ] Type checking passing
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Merged to main branch

---

**For full details, see `docs/07_PHASE_4_PLAN.md`**
