"""ROMA Orchestrator stub used by the FastAPI layer."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from app.schemas import (
    QueryRequest,
    RetrievedContext,
    SourceCitation,
    StreamEvent,
    TailorOutput,
)


class ROMAOrchestrator:
    """Small orchestration stub returning deterministic results for tests."""

    def __init__(self, *, stream_chunk_pause_ms: int = 0) -> None:
        self._stream_chunk_pause = stream_chunk_pause_ms / 1000

    async def run_query(self, request: QueryRequest) -> TailorOutput:
        """Generate a TailorOutput matching the system contract."""

        contexts = self._mock_retrieval(request.text)
        content = self._compose_content(request.text, contexts)
        citations = [
            SourceCitation(
                source_id=context.source_id,
                chunk_id=context.chunk_id,
                text_snippet=context.content,
                url=context.source_url,
            )
            for context in contexts
        ]

        return TailorOutput(
            content=content,
            citations=citations,
            tone_used=request.persona,
            follow_up_suggestions=[
                "Would you like a deeper dive into the cited sources?",
                "Should I draft follow-up ingestion tasks?",
            ],
            confidence_score=0.82,
        )

    async def stream_query(
        self, request: QueryRequest
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream SSE events for the query."""

        response = await self.run_query(request)
        for index, token in enumerate(response.content.split()):
            yield StreamEvent(event="token", data={"index": index, "token": token})
            await self._maybe_pause()

        yield StreamEvent(event="complete", data=response.model_dump())

    def _mock_retrieval(self, query_text: str) -> list[RetrievedContext]:
        """Simulate LanceDB retrieval with deterministic snippets."""

        normalized = query_text.lower()
        focus = "workflow" if "ingest" in normalized else "system overview"

        return [
            RetrievedContext(
                chunk_id="chunk-roma",
                content="ROMA orchestrator coordinates guardrails, memory, and the tailor.",
                source_id="roma_design_doc",
                source_url="https://docs.local/roma",
                relevance_score=0.95,
                metadata={"source_type": "local", "focus": focus},
            ),
            RetrievedContext(
                chunk_id="chunk-dolphin",
                content="Dolphin parser extracts layout-aware chunks for LanceDB indexing.",
                source_id="dolphin_ingestion_playbook",
                source_url="https://docs.local/dolphin",
                relevance_score=0.92,
                metadata={"source_type": "gdrive", "focus": "ingestion"},
            ),
        ]

    def _compose_content(
        self, query_text: str, contexts: list[RetrievedContext]
    ) -> str:
        """Build the natural language response content."""

        lines = [
            f"You asked: {query_text}",
            "Key findings grounded in the retrieved context:",
        ]
        for context in contexts:
            lines.append(f"- {context.content}")
        lines.append("Let me know if you would like follow-up actions.")
        return "\n".join(lines)

    async def _maybe_pause(self) -> None:
        """Optional pause inserted between streamed tokens."""

        if self._stream_chunk_pause > 0:
            await asyncio.sleep(self._stream_chunk_pause)
