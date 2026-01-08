"""ROMA Orchestrator implementation."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import TYPE_CHECKING, Protocol

from app.agents.tailor import TailorAgent
from app.exceptions import AgentFailureError
from app.guardrails import GuardrailsAgent
from app.memory import MemoryAgent
from app.schemas import (
    AgentFailure,
    ConversationState,
    ErrorCodes,
    GuardrailsInput,
    GuardrailsOutput,
    MemoryOutput,
    MemoryQuery,
    OrchestratorOutput,
    PlanStep,
    QueryRequest,
    RetrievedContext,
    StreamEvent,
    TailorInput,
    TailorOutput,
)
from app.services.llm import LLMService


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Sequence

    from app.schemas.base import PlanStatus


MAX_ROMA_DEPTH = 5
logger = logging.getLogger(__name__)


def _summary_formatting_instructions() -> str:
    return (
        "Provide a concise summary with 4-6 bullet points plus a one-sentence "
        "overview. Cite at least 3 distinct chunks when available."
    )


def _summary_min_citations(contexts: Sequence[RetrievedContext]) -> int:
    unique_content = {
        re.sub(r"\s+", " ", context.content).strip().lower()
        for context in contexts
        if context.content and context.content.strip()
    }
    unique_count = len(unique_content) or len(contexts)
    return max(1, min(3, unique_count))


class GuardrailsProtocol(Protocol):
    async def enforce(
        self, payload: GuardrailsInput
    ) -> GuardrailsOutput | AgentFailure:
        ...


class MemoryAgentProtocol(Protocol):
    async def query(self, query: MemoryQuery) -> MemoryOutput | AgentFailure:
        ...


class TailorProtocol(Protocol):
    async def process(self, payload: TailorInput) -> TailorOutput:
        ...

    async def stream_response(
        self, payload: TailorInput
    ) -> AsyncGenerator[str | AgentFailure, None]:
        ...

    def finalize_streamed_output(
        self, payload: TailorInput, content: str
    ) -> TailorOutput:
        ...


class ROMAOrchestrator:
    """ROMA planning/execution loop with guardrails, memory, and tailor integration."""

    def __init__(
        self,
        *,
        guardrails: GuardrailsProtocol | None = None,
        memory_agent: MemoryAgentProtocol | None = None,
        tailor_agent: TailorProtocol | None = None,
        llm_service: LLMService | None = None,
        stream_chunk_pause_ms: int = 0,
        state_store: dict[str, ConversationState] | None = None,
        max_depth: int = MAX_ROMA_DEPTH,
    ) -> None:
        from pathlib import Path

        self._guardrails = guardrails or GuardrailsAgent()
        # MemoryAgent requires db_path parameter - use default if not provided
        self._memory_agent = memory_agent or MemoryAgent(
            db_path=str(Path.cwd() / "data" / "lancedb")
        )
        self._tailor_agent = tailor_agent or TailorAgent()
        self._llm_service = llm_service or LLMService()
        self._stream_chunk_pause = stream_chunk_pause_ms / 1000
        self._state_store = state_store or {}
        self._max_depth = max_depth
        self._plan: list[PlanStep] = []

    async def run_query(self, request: QueryRequest) -> OrchestratorOutput:
        """Execute the ROMA loop and return an orchestrator output."""

        start = time.perf_counter()
        self._plan = []
        sanitized_query = await self._apply_input_guardrails(request.text)
        summary_mode = self._is_summary_query(sanitized_query)
        topics = await self._extract_topics(sanitized_query)
        attempt = 0
        last_error: AgentFailureError | None = None

        while attempt < self._max_depth:
            attempt += 1
            contexts, retrieval_error = await self._retrieve_contexts(
                sanitized_query, topics, attempt, summary=summary_mode
            )
            if retrieval_error:
                last_error = retrieval_error
            else:
                synth_result = await self._synthesize_and_verify(
                    sanitized_query, contexts, request.persona, attempt, summary=summary_mode
                )
                if isinstance(synth_result, TailorOutput):
                    total_ms = round((time.perf_counter() - start) * 1000, 2)
                    return OrchestratorOutput(
                        final_response=synth_result,
                        execution_plan=self._plan,
                        processing_time_total_ms=total_ms,
                    )
                last_error = synth_result

            if last_error is None:
                break
            if not last_error.failure.recoverable:
                raise last_error
            self._add_plan_step(
                description=(
                    f"Retry planning iteration {attempt + 1} due to "
                    f"{last_error.failure.error_code}"
                ),
                tool_call="orchestrator.retry",
                status="pending",
            )

        if last_error is None:
            last_error = AgentFailureError(
                agent_id="orchestrator.roma",
                error_code=ErrorCodes.TIMEOUT,
                message="ROMA planning exhausted without completion.",
                recoverable=False,
            )
        raise last_error

    async def stream_query(
        self, request: QueryRequest
    ) -> AsyncGenerator[StreamEvent, None]:
        """Run the orchestrator and emit SSE events."""

        self._plan = []
        try:
            sanitized_query = await self._apply_input_guardrails(request.text)
        except AgentFailureError as exc:
            yield StreamEvent(event="error", data=exc.failure.model_dump())
            return

        summary_mode = self._is_summary_query(sanitized_query)
        yield StreamEvent(event="thinking", data="Searching knowledge base...")
        topics = await self._extract_topics(sanitized_query)
        contexts, retrieval_error = await self._retrieve_contexts(
            sanitized_query, topics, attempt=1, summary=summary_mode
        )
        if retrieval_error:
            yield StreamEvent(event="error", data=retrieval_error.failure.model_dump())
            return

        if not contexts:
            failure = AgentFailure(
                agent_id="orchestrator.memory",
                error_code=ErrorCodes.MEMORY_NO_RESULTS,
                message="No context available after retrieval.",
                recoverable=True,
            )
            yield StreamEvent(event="error", data=failure.model_dump())
            return

        yield StreamEvent(event="thinking", data="Generating response...")
        tailor_input = TailorInput(
            user_query=sanitized_query,
            context_chunks=contexts,
            persona=request.persona,
            formatting_instructions=(
                _summary_formatting_instructions() if summary_mode else None
            ),
        )

        accumulated = ""
        async for token in self._tailor_agent.stream_response(tailor_input):
            if isinstance(token, AgentFailure):
                yield StreamEvent(event="error", data=token.model_dump())
                return
            accumulated += token
            yield StreamEvent(event="token", data=token)
            await self._maybe_pause()

        try:
            output = self._tailor_agent.finalize_streamed_output(
                tailor_input, accumulated
            )
            min_citations = _summary_min_citations(contexts) if summary_mode else 1
            self._verify_tailor_output(output, contexts, min_citations=min_citations)
            sanitized = await self._apply_output_guardrails(output)
        except AgentFailureError as exc:
            yield StreamEvent(event="error", data=exc.failure.model_dump())
            return

        yield StreamEvent(event="complete", data=sanitized.model_dump())

    async def _apply_input_guardrails(self, content: str) -> str:
        step = self._add_plan_step(
            description="Guardrails validation",
            tool_call="guardrails.enforce",
        )
        step.status = "in_progress"
        payload = GuardrailsInput(content=content, check_type="input_validation")
        try:
            result = await self._guardrails.enforce(payload)
        except AgentFailureError:
            step.status = "failed"
            raise
        if isinstance(result, AgentFailure):
            step.status = "failed"
            raise self._as_error(result)

        step.status = "completed"
        return result.sanitized_content or content

    async def _retrieve_contexts(
        self,
        query: str,
        topics: list[str],
        attempt: int,
        *,
        summary: bool = False,
    ) -> tuple[list[RetrievedContext], AgentFailureError | None]:
        """Execute memory retrieval for each topic."""

        contexts: list[RetrievedContext] = []
        targets = topics or [query]
        top_k = 12 if summary else 5
        min_score = 0.4 if summary else 0.7
        for topic in targets:
            step = self._add_plan_step(
                description=f"Retrieve context for '{topic}' (attempt {attempt})",
                tool_call="memory.query",
            )
            step.status = "in_progress"
            try:
                # MemoryAgent.query() takes a MemoryQuery object
                memory_query = MemoryQuery(
                    query_text=topic,
                    top_k=top_k,
                    min_relevance_score=min_score,
                    filters=None,
                )
                result = await self._memory_agent.query(memory_query)

                # Handle AgentFailure response
                if isinstance(result, AgentFailure):
                    if result.error_code == ErrorCodes.MEMORY_NO_RESULTS:
                        step.status = "failed"
                        relaxed_step = self._add_plan_step(
                            description=(
                                f"Relax retrieval threshold for '{topic}' "
                                f"(attempt {attempt})"
                            ),
                            tool_call="memory.query",
                        )
                        relaxed_step.status = "in_progress"
                        relaxed_query = MemoryQuery(
                            query_text=topic,
                            top_k=18 if summary else 8,
                            min_relevance_score=0.2 if summary else 0.3,
                            filters=None,
                        )
                        relaxed_result = await self._memory_agent.query(relaxed_query)
                        if isinstance(relaxed_result, AgentFailure):
                            relaxed_step.status = "failed"
                            raise self._as_error(relaxed_result)
                        relaxed_step.status = "completed"
                        result = relaxed_result
                    else:
                        step.status = "failed"
                        raise self._as_error(result)

                # Extract contexts from MemoryOutput
                contexts.extend(result.results)
            except AgentFailureError as exc:
                step.status = "failed"
                return [], exc
            step.status = "completed"

        return contexts, None

    async def _synthesize_and_verify(
        self,
        query: str,
        contexts: list[RetrievedContext],
        persona: str,
        attempt: int,
        *,
        summary: bool = False,
    ) -> TailorOutput | AgentFailureError:
        """Call the Tailor agent followed by verifier + output guardrails."""

        step = self._add_plan_step(
            description=f"Verifier + Synthesize attempt {attempt}",
            tool_call="tailor.process+verifier",
        )
        step.status = "in_progress"

        if not contexts:
            step.status = "failed"
            return AgentFailureError(
                agent_id="orchestrator.memory",
                error_code=ErrorCodes.MEMORY_NO_RESULTS,
                message="No context available after retrieval.",
                recoverable=True,
            )

        payload = TailorInput(
            user_query=query,
            context_chunks=contexts,
            persona=persona,  # type: ignore[arg-type]
            formatting_instructions=(
                _summary_formatting_instructions() if summary else None
            ),
        )
        try:
            response = await self._tailor_agent.process(payload)
            min_citations = _summary_min_citations(contexts) if summary else 1
            self._verify_tailor_output(response, contexts, min_citations=min_citations)
            sanitized = await self._apply_output_guardrails(response)
        except AgentFailureError as exc:
            step.status = "failed"
            return exc

        step.status = "completed"
        return sanitized

    async def _apply_output_guardrails(self, response: TailorOutput) -> TailorOutput:
        payload = GuardrailsInput(
            content=response.content,
            check_type="output_safety",
        )
        try:
            result = await self._guardrails.enforce(payload)
        except AgentFailureError:
            raise
        if isinstance(result, AgentFailure):
            raise self._as_error(result)
        if result.sanitized_content == response.content:
            return response
        return response.model_copy(update={"content": result.sanitized_content})

    def _verify_tailor_output(
        self,
        response: TailorOutput,
        contexts: Sequence[RetrievedContext],
        *,
        min_citations: int = 1,
    ) -> None:
        """Ensure the Tailor output is grounded in retrieved contexts."""

        if not response.citations or len(response.citations) < min_citations:
            raise AgentFailureError(
                agent_id="orchestrator.verifier",
                error_code=ErrorCodes.TAILOR_HALLUCINATION,
                message="Verifier rejected response: insufficient citations.",
                recoverable=True,
            )

        available_ids = {chunk.chunk_id for chunk in contexts}
        invalid = [
            citation.chunk_id
            for citation in response.citations
            if citation.chunk_id not in available_ids
        ]
        if invalid:
            raise AgentFailureError(
                agent_id="orchestrator.verifier",
                error_code=ErrorCodes.TAILOR_HALLUCINATION,
                message="Verifier rejected response: citation out of context.",
                recoverable=True,
                details={"invalid_chunks": invalid},
            )

    async def _extract_topics(self, query: str) -> list[str]:
        """Extract search topics from query using LLM-based understanding.

        First tries LLM-based extraction for better understanding,
        falls back to regex-based extraction if LLM fails.
        """
        # Try LLM-based topic extraction first
        llm_topics = await self._llm_extract_topics(query)
        if llm_topics:
            return llm_topics

        # Fallback to regex-based extraction for comparison queries
        lowered = query.lower()
        if not any(keyword in lowered for keyword in ("compare", " vs ", " versus ")):
            return []

        parts = re.split(r"\band\b|\bvs\b|\bversus\b", query, flags=re.IGNORECASE)
        topics: list[str] = []
        for part in parts:
            cleaned = re.sub(
                r"^(compare|versus|vs)\s+", "", part.strip(), flags=re.IGNORECASE
            )
            if cleaned:
                topics.append(cleaned)
        return topics[:5]

    async def _llm_extract_topics(self, query: str) -> list[str]:
        """Use LLM to extract search topics from query."""
        system_prompt = """You are a query analyzer for a RAG system.
Extract key search topics from the user's query.
Return a JSON array of 1-5 search topics (strings).

Examples:
Query: "What is the Q3 cloud budget?"
Output: ["Q3 cloud budget", "quarterly cloud spending"]

Query: "Compare AWS vs Azure pricing"
Output: ["AWS pricing", "Azure pricing"]

Query: "Tell me about the new feature"
Output: ["new feature"]

Return ONLY the JSON array, no explanation."""

        user_prompt = f"Query: {query}\nOutput:"

        result = await self._llm_service.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.3,
            max_tokens=200,
        )

        if isinstance(result, AgentFailure):
            logger.warning(
                "LLM topic extraction failed, using fallback",
                extra={
                    "agent_id": "orchestrator",
                    "error_code": result.error_code,
                },
            )
            return []

        # Parse JSON response
        try:
            topics = json.loads(result.strip())
            if isinstance(topics, list) and all(isinstance(t, str) for t in topics):
                return topics[:5]  # Limit to 5 topics
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse LLM topic extraction response",
                extra={"agent_id": "orchestrator", "response": result[:100]},
            )

        return []

    def _add_plan_step(
        self, *, description: str, tool_call: str, status: PlanStatus = "pending"
    ) -> PlanStep:
        step = PlanStep(
            step_id=len(self._plan) + 1,
            description=description,
            tool_call=tool_call,
            status=status,
        )
        self._plan.append(step)
        return step

    async def _maybe_pause(self) -> None:
        if self._stream_chunk_pause > 0:
            await asyncio.sleep(self._stream_chunk_pause)

    @staticmethod
    def _as_error(failure: AgentFailure) -> AgentFailureError:
        return AgentFailureError(
            agent_id=failure.agent_id,
            error_code=failure.error_code,
            message=failure.message,
            recoverable=failure.recoverable,
            details=failure.details,
        )

    @staticmethod
    def _is_summary_query(query: str) -> bool:
        lowered = query.lower()
        return any(
            keyword in lowered
            for keyword in ("summarize", "summary", "overview", "high-level", "tl;dr", "tldr")
        )


__all__ = ["ROMAOrchestrator", "MAX_ROMA_DEPTH"]
