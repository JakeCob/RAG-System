# Multi-Source Agentic RAG System

This repository hosts a full-stack Retrieval-Augmented Generation platform that combines a FastAPI backend (agents, ingestion, LanceDB vector store) with a Next.js 14 frontend. Phase 3 introduced a production-ready ROMA console so users can ingest documents, run queries, and inspect citations directly from the browser.

## Key Capabilities
- **ROMA Orchestrator**: Recursive planning loop that routes Guardrails → Memory → Tailor agents with strict grounding.
- **Dolphin Parsing Pipeline**: Layout-aware ingestion that preserves tables/images before chunking into LanceDB.
- **LanceDB Memory**: Embedded vector store with deterministic mocks for tests.
- **Next.js Frontend**: Persona-aware query form, grounded response viewer, ingestion card, and shared TypeScript schemas mirroring the backend.
- **Unified Contracts**: Pydantic models under `src/app/schemas/` are mirrored in `frontend/src/types/` ensuring API parity (including SSE envelopes and `AgentFailure` payloads).

## Repository Layout
```
docs/                     # Design, specs, ingestion, test plan, sprint backlog, frontend playbook
frontend/                 # Next.js 14 app router project
└── src/
    ├── app/              # Pages (ROMA console, global styles)
    ├── lib/api.ts        # Typed API client for /health, /query, /ingest
    └── types/index.ts    # Frontend mirrors of backend Pydantic schemas
src/app/                  # FastAPI application + agents
├── agents/               # ROMA orchestrator, Tailor agent
├── api/                  # FastAPI routes (/health, /query, /ingest)
├── config/               # Pydantic settings + env helpers
├── guardrails/           # Input/output safety enforcement
├── ingestion/            # Async ingestion service
├── memory/               # LanceDB integration (embedded)
├── parser/               # Dolphin parser (layout-aware)
└── schemas/              # Authoritative contracts shared by all agents
tests/                    # Unit, API, and integration tests (with mocks)
start.sh                  # Convenience script to boot backend + frontend together
```

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm 9+

### Install Dependencies
```bash
# Backend (from repo root)
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Frontend
cd frontend
npm install
cd ..
```

### Run the Stack
- **One command**: `./start.sh` (starts FastAPI on :8000 and Next.js on :3000 with reload).
- **Manual**:
  - Backend: `uvicorn app.api:app --app-dir src --host 0.0.0.0 --port 8000 --reload`
  - Frontend: `cd frontend && npm run dev`

Visit http://localhost:3000 to load the ROMA console. Health badges are fetched from `GET /health`, queries hit `POST /query`, and documents upload through `POST /ingest` (requires Bearer token from `ingest_auth_token` setting).

### Testing & Quality Gates
```bash
# Backend lint + type check
ruff check src/ tests/
mypy src/
pytest

# Frontend
cd frontend
npm run lint
npm run typecheck
npm run test
```

## Documentation Map
- `docs/01_DESIGN_DOC.md` – Architecture, data flow, updated with frontend experience.
- `docs/02_AGENT_SPECS.md` – Agent contracts, schemas, API payloads (authoritative).
- `docs/03_INGESTION_STRATEGY.md` – Dolphin parsing & chunking pipeline.
- `docs/04_TEST_PLAN.md` – QA plan incl. new frontend/API contract tests.
- `docs/05_SPRINT_BACKLOG.md` – Sprint backlog with P3 tasks.
- `docs/06_FRONTEND_PLAYBOOK.md` – **New**: Frontend integration guide (types, API client, UI flow).
- `AGENTS.md` – Quick-start guide for multi-agent workflows.
- `CLAUDE.md` – Instructions for Claude Code contributions.

Refer to these docs before making changes—they define acceptance criteria for every component. 
