"""Tailor Agent - deterministic synthesis with grounding.

Implements the persona-aware response generator described in docs/02_AGENT_SPECS.md.
Ensures every statement is grounded in retrieved context and emits citations to
avoid hallucinations.
"""

from __future__ import annotations

from statistics import fmean
from typing import Iterable

from app.exceptions import AgentFailureError
from app.schemas import ErrorCodes, RetrievedContext, SourceCitation, TailorInput, TailorOutput


class TailorAgent:
    """Persona-aware response synthesizer.

    The agent is intentionally deterministic to keep unit tests stable. It synthesizes
    the retrieved context into a Markdown response and attaches citations for every
    referenced chunk. When insufficient grounding is available, the agent raises
    `AgentFailureError` with `ERR_TAILOR_HALLUCINATION`.
    """

    def __init__(self, *, agent_id: str = "tailor") -> None:
        self._agent_id = agent_id

    async def process(self, payload: TailorInput) -> TailorOutput:
        """Generate a grounded TailorOutput or raise AgentFailureError."""

        context = payload.context_chunks
        if not context:
            raise AgentFailureError(
                agent_id=self._agent_id,
                error_code=ErrorCodes.TAILOR_HALLUCINATION,
                message="No context available to ground the response.",
                recoverable=False,
            )

        unique_context = _deduplicate_context(context)
        response_lines = [
            f"Tone: {payload.persona}",
            f"User query: {payload.user_query}",
            "Grounded findings:",
        ]

        citations = [
            SourceCitation(
                source_id=chunk.source_id,
                chunk_id=chunk.chunk_id,
                text_snippet=chunk.content[:200],
                url=chunk.source_url,
            )
            for chunk in unique_context
        ]

        for chunk in unique_context:
            response_lines.append(f"- {chunk.content}")

        if payload.formatting_instructions:
            response_lines.append("")
            response_lines.append(f"Formatting note: {payload.formatting_instructions}")

        followups = [
            "Would you like a deeper dive on any cited source?",
            "Should I prepare follow-up ingestion tasks?",
        ]

        confidence = _calculate_confidence(unique_context)

        return TailorOutput(
            content="\n".join(response_lines),
            citations=citations,
            tone_used=payload.persona,
            follow_up_suggestions=followups,
            confidence_score=confidence,
        )


def _deduplicate_context(chunks: Iterable[RetrievedContext]) -> list[RetrievedContext]:
    """Return context chunks without duplicate chunk_ids."""

    seen: set[str] = set()
    ordered: list[RetrievedContext] = []
    for chunk in chunks:
        if chunk.chunk_id in seen:
            continue
        seen.add(chunk.chunk_id)
        ordered.append(chunk)
    return ordered


def _calculate_confidence(chunks: Iterable[RetrievedContext]) -> float:
    """Compute a deterministic confidence score based on relevance."""

    scores = [chunk.relevance_score for chunk in chunks]
    base = fmean(scores) if scores else 0.5
    # Keep value in [0, 1]
    return max(0.35, min(0.98, round(base, 2)))


__all__ = ["TailorAgent"]

