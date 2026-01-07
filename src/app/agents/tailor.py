"""Tailor Agent - LLM-powered synthesis with grounding.

Implements the persona-aware response generator described in docs/02_AGENT_SPECS.md.
Ensures every statement is grounded in retrieved context and emits citations to
avoid hallucinations.
"""

from __future__ import annotations

import logging
import re
from statistics import fmean
from typing import TYPE_CHECKING

from app.exceptions import AgentFailureError
from app.schemas import (
    AgentFailure,
    ErrorCodes,
    RetrievedContext,
    SourceCitation,
    TailorInput,
    TailorOutput,
)
from app.services.llm import LLMService


if TYPE_CHECKING:
    from collections.abc import Iterable


logger = logging.getLogger(__name__)


class TailorAgent:
    """Persona-aware response synthesizer using LLM.

    Uses LLM to synthesize retrieved context into a grounded response with
    proper citations. Validates that all citations reference actual context chunks
    to avoid hallucinations.
    """

    def __init__(
        self, *, agent_id: str = "tailor", llm_service: LLMService | None = None
    ) -> None:
        self._agent_id = agent_id
        self._llm_service = llm_service or LLMService()

    async def process(self, payload: TailorInput) -> TailorOutput:
        """Generate a grounded TailorOutput using LLM or raise AgentFailureError."""
        context = payload.context_chunks
        if not context:
            raise AgentFailureError(
                agent_id=self._agent_id,
                error_code=ErrorCodes.TAILOR_HALLUCINATION,
                message="No context available to ground the response.",
                recoverable=False,
            )

        unique_context = _deduplicate_context(context)

        # Build context text with citations
        context_text = self._build_context_text(unique_context)

        # Generate response using LLM
        system_prompt = self._build_system_prompt(payload.persona)
        user_prompt = self._build_user_prompt(
            payload.user_query, context_text, payload.formatting_instructions
        )

        result = await self._llm_service.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.7,
            max_tokens=2048,
        )

        if isinstance(result, AgentFailure):
            logger.error(
                "LLM synthesis failed",
                extra={
                    "agent_id": self._agent_id,
                    "error_code": result.error_code,
                },
            )
            raise AgentFailureError(
                agent_id=self._agent_id,
                error_code=result.error_code,
                message=f"LLM synthesis failed: {result.message}",
                recoverable=result.recoverable,
                details=result.details,
            )

        # Extract citations from response
        citations = self._extract_citations(result, unique_context)

        # Validate citations are grounded
        if not citations:
            logger.warning(
                "LLM response missing citations",
                extra={"agent_id": self._agent_id, "response": result[:200]},
            )
            raise AgentFailureError(
                agent_id=self._agent_id,
                error_code=ErrorCodes.TAILOR_HALLUCINATION,
                message="LLM response missing required citations",
                recoverable=True,
            )

        # Generate follow-up suggestions
        followups = self._generate_followups(payload.user_query)

        # Calculate confidence
        confidence = _calculate_confidence(unique_context)

        return TailorOutput(
            content=result,
            citations=citations,
            tone_used=payload.persona,
            follow_up_suggestions=followups,
            confidence_score=confidence,
        )

    def _build_system_prompt(self, persona: str) -> str:
        """Build system prompt for LLM synthesis."""
        return f"""You are a helpful assistant that synthesizes grounded \
answers from retrieved context.

Persona: {persona}
- Technical: Use precise terminology, include technical details
- Executive: Focus on high-level insights, business impact
- General: Balance clarity and detail for general audience

CRITICAL RULES:
1. ONLY use information from the provided context chunks
2. Cite sources using [1], [2], etc. corresponding to chunk indices
3. If context is insufficient, state "I don't have enough information \
to answer this question."
4. Be concise and accurate
5. ALWAYS include at least one citation in your response

Example:
Context:
[1] The Q3 cloud budget is $45,000... (Source: budget_doc)
[2] AWS spending increased 15% in Q3... (Source: cloud_report)

Question: What is the Q3 cloud budget?
Answer: The Q3 cloud budget is $45,000 [1]. AWS spending contributed \
to a 15% increase in Q3 [2]."""

    def _build_user_prompt(
        self, query: str, context_text: str, formatting_instructions: str | None
    ) -> str:
        """Build user prompt for LLM synthesis."""
        prompt = f"""Question: {query}

Context:
{context_text}

Synthesize a grounded answer with citations."""

        if formatting_instructions:
            prompt += f"\n\nFormatting: {formatting_instructions}"

        return prompt

    def _build_context_text(self, chunks: list[RetrievedContext]) -> str:
        """Build formatted context text with indices for citation."""
        lines = []
        for i, chunk in enumerate(chunks, 1):
            lines.append(
                f"[{i}] {chunk.content} (Source: {chunk.source_id}, "
                f"URL: {chunk.source_url or 'N/A'})"
            )
        return "\n\n".join(lines)

    def _extract_citations(
        self, response: str, chunks: list[RetrievedContext]
    ) -> list[SourceCitation]:
        """Extract citation markers from response and map to chunks."""
        # Find all citation markers like [1], [2], etc.
        citation_pattern = r"\[(\d+)\]"
        matches = re.findall(citation_pattern, response)

        citations: list[SourceCitation] = []
        seen_indices: set[int] = set()

        for match in matches:
            idx = int(match) - 1  # Convert to 0-based index
            if idx < 0 or idx >= len(chunks):
                logger.warning(
                    "Invalid citation index",
                    extra={
                        "agent_id": self._agent_id,
                        "index": idx + 1,
                        "total_chunks": len(chunks),
                    },
                )
                continue

            if idx in seen_indices:
                continue  # Skip duplicate citations
            seen_indices.add(idx)

            chunk = chunks[idx]
            citations.append(
                SourceCitation(
                    source_id=chunk.source_id,
                    chunk_id=chunk.chunk_id,
                    text_snippet=chunk.content[:200],
                    url=chunk.source_url,
                )
            )

        return citations

    def _generate_followups(self, query: str) -> list[str]:
        """Generate follow-up suggestions based on query."""
        # Simple rule-based follow-ups (could be enhanced with LLM in future)
        followups = ["Would you like more details on any specific aspect?"]

        query_lower = query.lower()
        if "compare" in query_lower or " vs " in query_lower:
            followups.append("Would you like a detailed comparison table?")
        if "how" in query_lower or "why" in query_lower:
            followups.append("Should I explain the underlying mechanisms?")
        if "budget" in query_lower or "cost" in query_lower:
            followups.append("Would you like a breakdown of the costs?")

        return followups[:3]  # Limit to 3 suggestions


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
