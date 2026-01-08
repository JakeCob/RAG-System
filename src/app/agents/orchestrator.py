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
        topics = await self._extract_topics(sanitized_query)
        attempt = 0
        last_error: AgentFailureError | None = None

        while attempt < self._max_depth:
            attempt += 1
            contexts, retrieval_error = await self._retrieve_contexts(
                sanitized_query, topics, attempt
            )
            if retrieval_error:
                last_error = retrieval_error
            else:
                synth_result = await self._synthesize_and_verify(
                    sanitized_query, contexts, request.persona, attempt
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

        try:
            result = await self.run_query(request)
        except AgentFailureError as exc:
            yield StreamEvent(event="error", data=exc.failure.model_dump())
            return

        response = result.final_response
        for index, token in enumerate(response.content.split()):
            yield StreamEvent(event="token", data={"index": index, "token": token})
            await self._maybe_pause()

        yield StreamEvent(event="complete", data=response.model_dump())

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
        self, query: str, topics: list[str], attempt: int
    ) -> tuple[list[RetrievedContext], AgentFailureError | None]:
        """Execute memory retrieval for each topic."""

        contexts: list[RetrievedContext] = []
        targets = topics or [query]
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
                    top_k=5,
                    min_relevance_score=0.7,
                    filters=None,
                )
                result = await self._memory_agent.query(memory_query)

                # Handle AgentFailure response
                if isinstance(result, AgentFailure):
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
        )
        try:
            response = await self._tailor_agent.process(payload)
            self._verify_tailor_output(response, contexts)
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
        self, response: TailorOutput, contexts: Sequence[RetrievedContext]
    ) -> None:
        """Ensure the Tailor output is grounded in retrieved contexts."""

        if not response.citations:
            raise AgentFailureError(
                agent_id="orchestrator.verifier",
                error_code=ErrorCodes.TAILOR_HALLUCINATION,
                message="Verifier rejected response: missing citations.",
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


__all__ = ["ROMAOrchestrator", "MAX_ROMA_DEPTH"]
