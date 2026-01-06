# Phase 4 Task Dependency Diagram

## Visual Task Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PHASE 4 START                                │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                   ┌──────────────┼──────────────┐
                   │              │              │
                   ▼              ▼              ▼
         ┌───────────────┐ ┌───────────┐ ┌─────────────┐
         │   P4-2        │ │   P4-3    │ │   P4-4      │
         │   GDrive      │ │   Web     │ │   Parser    │
         │   Connector   │ │   Scraper │ │   Expansion │
         └───────┬───────┘ └─────┬─────┘ └──────┬──────┘
                 │               │              │
                 └───────────┬───┴──────┬───────┘
                             │          │
         ┌───────────────────┤          │
         │                   │          │
         │    ┌──────────────┘          │
         │    │                         │
         ▼    ▼                         ▼
    ┌──────────────┐           ┌────────────────┐
    │   P4-1       │           │   P4-7         │
    │   LLM        │◄──────────│   Observability│
    │   Integration│           │   & Logging    │
    └──────┬───────┘           └────────────────┘
           │                            ▲
           │                            │
           ▼                            │
    ┌──────────────┐                   │
    │   P4-5       │                   │
    │   Streaming  │                   │
    │   Queries    │                   │
    └──────┬───────┘                   │
           │                            │
           │    ┌──────────────────────┐│
           │    │                       │
           ▼    ▼                       │
    ┌──────────────┐           ┌────────────┐
    │   P4-6       │           │   P4-8     │
    │   Golden     │           │   Error    │
    │   Dataset    │           │   Hardening│
    └──────┬───────┘           └────────────┘
           │                            ▲
           │                            │
           ▼                            │
    ┌──────────────┐                   │
    │   P4-9       │                   │
    │   Frontend   │◄──────────────────┘
    │   UX         │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │   P4-10      │
    │   Coverage   │
    │   & Docs     │
    └──────┬───────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE 4 COMPLETE ✅                               │
│               (Ready for Production Deployment)                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Task Groups

### 🟢 Foundation (Start Immediately, No Dependencies)
- **P4-1:** LLM Integration (OpenAI/Anthropic)
- **P4-2:** GDrive Connector (OAuth2)
- **P4-3:** Web Connector (Crawl4AI)
- **P4-4:** Parser Expansion (PDF/DOCX/PPTX/XLSX/EPUB)
- **P4-7:** Observability (Logging, Health Checks)
- **P4-8:** Error Hardening (AgentFailure standardization)

### 🟡 Mid-Phase (Requires Foundation)
- **P4-5:** Streaming Queries (requires P4-1 for LLM streaming)
- **P4-6:** Golden Dataset (requires P4-1, P4-2, P4-3, P4-4 for full stack)

### 🔴 Final Phase (Requires Most Components)
- **P4-9:** Frontend UX (requires P4-5 for streaming UI)
- **P4-10:** Coverage & Docs (requires all tasks complete)

---

## Critical Path (Longest Dependency Chain)

```
P4-1 (LLM) → P4-5 (Streaming) → P4-6 (Golden Dataset) → P4-9 (Frontend UX) → P4-10 (Docs)
```

**Estimated Timeline:** 2-3 weeks (assuming 2-3 days per task on critical path)

---

## Parallel Work Opportunities

### Week 1 (Kickoff)
**Sprint Goal:** Foundation Infrastructure

**Team A (Backend Core):**
- P4-1: LLM Integration
- P4-7: Observability
- P4-8: Error Hardening

**Team B (Ingestion):**
- P4-2: GDrive Connector
- P4-3: Web Connector
- P4-4: Parser Expansion

**Expected Completion:** 4-5 tasks by end of Week 1

---

### Week 2 (Integration)
**Sprint Goal:** End-to-End Functionality

**Team A (Backend + Frontend):**
- P4-5: Streaming Queries (depends on P4-1 ✅)
- P4-9: Frontend UX (depends on P4-5)

**Team B (Quality):**
- P4-6: Golden Dataset (depends on P4-1, P4-2, P4-3, P4-4 ✅)
- P4-10: Coverage analysis (start early, finalize later)

**Expected Completion:** 3-4 tasks by end of Week 2

---

### Week 3 (Polish & Launch)
**Sprint Goal:** Production Ready

**All Teams:**
- P4-10: Finalize coverage, update docs
- Integration testing across all components
- Smoke testing in staging environment
- Stakeholder demo & sign-off

**Expected Completion:** Phase 4 exit criteria met ✅

---

## Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| P4-1 | None | P4-5, P4-6, P4-7 |
| P4-2 | None | P4-6 |
| P4-3 | None | P4-6 |
| P4-4 | None | P4-6 |
| P4-5 | P4-1 | P4-9 |
| P4-6 | P4-1, P4-2, P4-3, P4-4 | P4-10 |
| P4-7 | P4-1 | None |
| P4-8 | None | None |
| P4-9 | P4-5 | P4-10 |
| P4-10 | All tasks | Phase 5 |

---

## Resource Allocation Suggestions

### Backend Engineers (3)
- **Engineer 1:** P4-1 (LLM) → P4-5 (Streaming) → P4-7 (Observability)
- **Engineer 2:** P4-2 (GDrive) → P4-4 (Parser) → P4-6 (Golden Dataset)
- **Engineer 3:** P4-3 (Web) → P4-8 (Error Hardening) → P4-6 (Golden Dataset)

### Frontend Engineers (1-2)
- **Engineer 4:** P4-9 (Frontend UX) → P4-10 (Frontend Tests & Docs)

### QA Engineer (1)
- **Engineer 5:** P4-6 (Golden Dataset) → P4-10 (Coverage Analysis) → Integration Testing

---

## Velocity Assumptions

**Task Sizes (Story Points):**
- P4-1 (LLM): 5 points (complex, foundational)
- P4-2 (GDrive): 5 points (OAuth complexity)
- P4-3 (Web): 3 points (straightforward with libraries)
- P4-4 (Parser): 5 points (multiple formats, table serialization)
- P4-5 (Streaming): 3 points (SSE implementation)
- P4-6 (Golden Dataset): 5 points (requires full stack, LLM-as-judge)
- P4-7 (Observability): 3 points (logging + health checks)
- P4-8 (Error Hardening): 3 points (refactoring existing code)
- P4-9 (Frontend UX): 5 points (citations, streaming UI, alerts)
- P4-10 (Coverage & Docs): 3 points (analysis + writing)

**Total:** 40 story points

**Assuming:**
- Team velocity: 15-20 points/week (5 engineers)
- **Timeline:** 2-3 weeks

---

## Risk-Adjusted Timeline

### Optimistic (Best Case): 2 weeks
- No blockers
- All integrations smooth
- High team velocity

### Realistic (Expected): 2.5 weeks
- Minor blockers (OAuth debugging, LLM rate limits)
- Expected learning curve for new libraries
- Moderate team velocity

### Pessimistic (Worst Case): 3-4 weeks
- Major blockers (GDrive API issues, Crawl4AI limitations)
- Unexpected test failures
- Lower team velocity or resource constraints

**Recommendation:** Plan for 3 weeks, aim for 2.5 weeks.

---

## Milestone Checkpoints

### Checkpoint 1 (End of Week 1)
**Goal:** Foundation Complete
- [ ] P4-1 complete (LLM operational)
- [ ] P4-2, P4-3, P4-4 at least 2/3 complete (ingestion paths working)
- [ ] P4-7, P4-8 in progress

**Go/No-Go:** If P4-1 incomplete, delay P4-5 and P4-6.

---

### Checkpoint 2 (End of Week 2)
**Goal:** Integration Complete
- [ ] P4-5 complete (streaming working)
- [ ] P4-6 in progress (golden dataset defined, tests running)
- [ ] P4-9 in progress (frontend streaming UI)

**Go/No-Go:** If P4-6 shows <70% accuracy, investigate retrieval/LLM issues before proceeding.

---

### Checkpoint 3 (End of Week 3)
**Goal:** Production Ready
- [ ] All tasks complete (P4-1 through P4-10)
- [ ] All exit criteria met
- [ ] Stakeholder demo passed
- [ ] Deployment plan reviewed

**Go/No-Go:** If coverage <80% or golden dataset <85%, extend timeline for hardening.

---

## Communication Plan

### Daily (15 min)
- Standup: Progress, blockers, help needed
- Focus on dependency chains (e.g., "P4-1 blocked? P4-5 and P4-6 at risk")

### Weekly (1 hour)
- Sprint review: Demo completed tasks
- Sprint planning: Adjust priorities based on progress
- Risk review: Update risk register, mitigation actions

### Phase End (2 hours)
- Comprehensive demo to stakeholders
- Retrospective: What went well, what to improve
- Phase 5 kickoff planning

---

## Success Criteria (Reaffirmed)

✅ All 10 tasks complete
✅ All quality gates passing
✅ Test coverage ≥80%
✅ Golden dataset accuracy ≥85%
✅ Query latency P95 <10s
✅ Deployable to staging environment
✅ Stakeholder sign-off

**Phase 4 Complete = Production Ready System**

---

**Next:** Start P4-1 (LLM Integration) 🚀
