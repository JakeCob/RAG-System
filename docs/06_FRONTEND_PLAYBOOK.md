# Frontend Playbook (Phase 3)

This document captures the conventions introduced when the ROMA console shipped in Phase 3. It should be kept in sync with any future Next.js or TypeScript changes.

## 1. Architecture Overview
- **Framework**: Next.js 14 App Router (React 18, strict mode).
- **Styling**: Tailwind CSS with utility-first classes; no custom CSS modules yet.
- **Type Safety**: `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` enforced via `tsconfig.json`.
- **Shared Types**: `frontend/src/types/index.ts` mirrors `src/app/schemas/` plus API-specific models (`HealthStatus`, `QueryRequest`, `StreamEvent`, `IngestResponse`).
- **Data Layer**: `frontend/src/lib/api.ts` centralizes all fetch calls, SSE parsing, and `AgentFailure` normalization.
- **Entry Point**: `frontend/src/app/page.tsx` renders the ROMA console (query form + ingestion flow).

## 2. Directory Guide
```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx         # Root layout (fonts, metadata)
│   │   ├── globals.css        # Tailwind base + CSS vars
│   │   └── page.tsx           # ROMA console UI
│   ├── lib/
│   │   └── api.ts             # API helpers (health/query/ingest + SSE)
│   ├── test/
│   │   └── setup.ts           # Vitest globals & Next router mocks
│   └── types/
│       └── index.ts           # Shared TypeScript contracts
└── ...
```

## 3. API Contracts
- **Health** (`GET /health`): Returns `HealthStatus { db, agents }`.
- **Query** (`POST /query`):
  - Request: `{ text: string; persona: "General"|"Technical"|"Executive"; stream?: boolean }`.
  - Sync Response: `TailorOutput`.
  - Streaming: SSE events with `{ event: "token"|"complete"|"error", data: ... }`.
- **Ingest** (`POST /ingest` with Bearer token + multipart file):
  - Success: `IngestResponse { task_id, filename, status }`.
  - Errors: Standardized `AgentFailure` JSON bubbled up to the UI.
- The API client MUST be updated whenever backend schemas evolve to keep the ROMA console functional.

## 4. UI Flow
1. **System Status Card**
   - Fires on mount, calling `getHealth()`.
   - Gracefully degrades to "Unable to load system status" if backend is offline.
2. **Ask ROMA Form**
   - Persona dropdown (General default) + textarea (validation: non-empty).
   - Submit triggers `submitQuery` and shows either Tailor output or `AgentFailure` alert.
   - Response card renders tone, confidence, content, follow-up pills, citations, and chunk metadata.
3. **Ingestion Form**
   - File input (pdf/docx/pptx/txt/md/xlsx/xls/csv) + Bearer token field.
   - Uses `ingestDocument` helper; surfaces validation copy for missing inputs and success state with queued task info.
4. **Error Handling**
   - All `AgentFailure` payloads are displayed verbatim with code + message + agent_id.
   - Non-AgentFailure errors bubble into toast-like copy at the component level.

## 5. Developer Workflow
```bash
cd frontend
npm install
npm run lint
npm run typecheck
npm run test
npm run dev
```
- Use `./start.sh` at the repo root to run backend + frontend simultaneously.
- Keep Vitest mocks (`src/test/setup.ts`) aligned with Next.js updates.
- When adding new components/routes, co-locate them under `src/app/` and update this document.

## 6. Testing Expectations
- Component tests should cover stateful logic (query form validation, ingestion notice rendering, citation lists).
- Integration/e2e tests (Playwright/Cypress) must verify:
  - Successful ingestion through `/ingest`.
  - Persona-driven ROMA answers with citations.
  - Guardrail failures surfacing `AgentFailure` alerts.
- QA uses the ROMA console as part of `docs/04_TEST_PLAN.md` Section 5; keep that doc synchronized when flows change.
