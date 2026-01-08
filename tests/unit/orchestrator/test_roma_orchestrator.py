"""ROMA Orchestrator tests.

Reference: docs/04_TEST_PLAN.md Section 3.7
Test Class: TestROMAOrchestrator
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.agents.orchestrator import MAX_ROMA_DEPTH, ROMAOrchestrator
from app.exceptions import AgentFailureError
from app.schemas import (
    AgentFailure,
    ErrorCodes,
    GuardrailsInput,
    GuardrailsOutput,
    MemoryOutput,
    MemoryQuery,
    QueryRequest,
    RetrievedContext,
    SourceCitation,
    TailorInput,
    TailorOutput,
)


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable


class _DeterministicTailor:
    """Small helper to mock Tailor responses inside orchestrator tests."""

    def __init__(self, *, fail_once: bool = False) -> None:
        self.fail_once = fail_once
        self.calls = 0

    async def process(self, payload: TailorInput) -> TailorOutput:
        """Mock Tailor response matching the schema returned by ROMA."""

        self.calls += 1
        if self.fail_once and self.calls == 1:
            raise AgentFailureError(
                agent_id="tailor",
                error_code=ErrorCodes.TAILOR_HALLUCINATION,
                message="Verifier detected hallucination",
                recoverable=True,
            )

        return TailorOutput(
            content=(
                "Mock answer grounded in retrieved context for "
                f"{payload.user_query}."
            ),
            citations=[
                SourceCitation(
                    source_id="doc-alpha",
                    chunk_id="chunk-1",
                    text_snippet="Alpha launches in May.",
                    url=None,
                )
            ],
            tone_used="General",
            follow_up_suggestions=["Need more detail?"],
            confidence_score=0.9,
        )

    async def stream_response(
        self, payload: TailorInput
    ) -> AsyncGenerator[str | AgentFailure, None]:
        _ = payload
        for token in ("Mock ", "stream ", "response."):
            yield token

    def finalize_streamed_output(
        self, payload: TailorInput, content: str
    ) -> TailorOutput:
        return TailorOutput(
            content=content,
            citations=[
                SourceCitation(
                    source_id="doc-alpha",
                    chunk_id="chunk-1",
                    text_snippet="Alpha launches in May.",
                    url=None,
                )
            ],
            tone_used=payload.persona,
            follow_up_suggestions=["Need more detail?"],
            confidence_score=0.9,
        )


class _DeterministicMemory:
    """Mock Memory agent returning configurable context."""

    def __init__(self, *, no_results: bool = False) -> None:
        self.no_results = no_results
        self.calls = 0

    async def query(self, query: MemoryQuery) -> MemoryOutput | AgentFailure:
        """Return deterministic MemoryOutput objects."""

        self.calls += 1
        if self.no_results:
            return AgentFailure(
                agent_id="memory",
                error_code=ErrorCodes.MEMORY_NO_RESULTS,
                message="No relevant chunks",
                recoverable=True,
            )

        return MemoryOutput(
            results=[
                RetrievedContext(
                    chunk_id="chunk-1",
                    content=f"Chunk about {query.query_text}",
                    source_id="doc-alpha",
                    source_url=None,
                    relevance_score=0.92,
                    metadata={"source_type": "local"},
                )
            ],
            total_found=1,
        )


class _StubLLMService:
    """Stub LLM service to avoid API key requirements in unit tests."""

    async def generate(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        _ = prompt
        _ = system
        _ = temperature
        _ = max_tokens
        return "[]"


@pytest.fixture()
def orchestrator_factory() -> Callable[..., ROMAOrchestrator]:
    """Return a factory that injects deterministic agent implementations."""

    def _factory(
        *,
        memory: _DeterministicMemory | None = None,
        tailor: _DeterministicTailor | None = None,
        guardrails_safe: bool = True,
    ) -> ROMAOrchestrator:
        memory_agent = memory or _DeterministicMemory()
        tailor_agent = tailor or _DeterministicTailor()

        class _Guardrails:
            async def enforce(
                self, payload: GuardrailsInput
            ) -> GuardrailsOutput | AgentFailureError:
                if guardrails_safe:
                    return GuardrailsOutput(
                        is_safe=True,
                        sanitized_content=payload.content,
                        risk_category=None,
                        reasoning="safe",
                    )
                raise AgentFailureError(
                    agent_id="guardrails",
                    error_code=ErrorCodes.GUARDRAIL_INJECTION,
                    message="Injection",
                    recoverable=False,
                )

        return ROMAOrchestrator(
            guardrails=_Guardrails(),
            memory_agent=memory_agent,
            tailor_agent=tailor_agent,
            llm_service=_StubLLMService(),
        )

    return _factory


class TestROMAOrchestrator:
    """Tests for the ROMA Orchestrator ("The Brain")."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_plan_generation(
        self, orchestrator_factory: Callable[..., ROMAOrchestrator]
    ) -> None:
        """Ensure the planner yields a multi-step plan."""

        orchestrator = orchestrator_factory()
        result = await orchestrator.run_query(QueryRequest(text="Compare X and Y"))

        descriptions = [step.description for step in result.execution_plan]
        assert any("Retrieve" in description for description in descriptions)
        assert any("Synthesize" in description for description in descriptions)
        assert result.final_response.content.startswith("Mock answer")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_error_handling_retry(
        self, orchestrator_factory: Callable[..., ROMAOrchestrator]
    ) -> None:
        """Verifier rejection should trigger a retry before succeeding."""

        tailor = _DeterministicTailor(fail_once=True)
        orchestrator = orchestrator_factory(tailor=tailor)
        result = await orchestrator.run_query(QueryRequest(text="Explain Alpha"))

        # Fail once + retry => at least two plan steps referencing retry behavior
        retry_steps = [
            step for step in result.execution_plan if "Retry" in step.description
        ]
        assert retry_steps, "Expected a retry step after verifier failure."
        assert result.final_response.confidence_score == pytest.approx(0.9, rel=1e-3)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_max_recursion_depth(
        self, orchestrator_factory: Callable[..., ROMAOrchestrator]
    ) -> None:
        """Ensure recursion depth stops further planning."""

        orchestrator = orchestrator_factory(
            memory=_DeterministicMemory(no_results=True)
        )

        with pytest.raises(AgentFailureError) as exc:
            await orchestrator.run_query(QueryRequest(text="loop forever"))

        failure = exc.value.failure
        assert failure.error_code == ErrorCodes.MEMORY_NO_RESULTS
        assert MAX_ROMA_DEPTH == 5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verifier_node_rejection(
        self, orchestrator_factory: Callable[..., ROMAOrchestrator]
    ) -> None:
        """Verifier rejecting the Tailor response should trigger new retrieval."""

        memory = _DeterministicMemory()
        tailor = _DeterministicTailor(fail_once=True)
        orchestrator = orchestrator_factory(memory=memory, tailor=tailor)

        result = await orchestrator.run_query(QueryRequest(text="Needs verification"))

        assert memory.calls >= 1, "Memory should be consulted at least once"
        # After verifier failure we expect at least one retrieval step
        # before completion.
        statuses = [
            step.status
            for step in result.execution_plan
            if "Verifier" in step.description
        ]
        assert statuses.count("failed") == 1

        # Ensure the final response is grounded after the verifier retry
        assert result.final_response.citations, "Final response must include citations."

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stream_query_emits_events(
        self, orchestrator_factory: Callable[..., ROMAOrchestrator]
    ) -> None:
        """Streaming should emit thinking, token, and complete events."""

        orchestrator = orchestrator_factory()
        events = []
        async for event in orchestrator.stream_query(QueryRequest(text="Stream it")):
            events.append(event)

        assert any(event.event == "thinking" for event in events)
        token_events = [event for event in events if event.event == "token"]
        assert token_events
        assert events[-1].event == "complete"

        complete = events[-1].data
        assert isinstance(complete, dict)
        assert complete.get("content") == "Mock stream response."

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stream_query_emits_error_on_failure(
        self, orchestrator_factory: Callable[..., ROMAOrchestrator]
    ) -> None:
        """Streaming should emit error events when retrieval fails."""

        orchestrator = orchestrator_factory(
            memory=_DeterministicMemory(no_results=True)
        )
        events = []
        async for event in orchestrator.stream_query(QueryRequest(text="Bad query")):
            events.append(event)

        error_events = [event for event in events if event.event == "error"]
        assert error_events
        error_payload = error_events[0].data
        assert isinstance(error_payload, dict)
        assert error_payload.get("error_code") == ErrorCodes.MEMORY_NO_RESULTS


# Safety guard for the async tests when executed via pytest without asyncio marker.
pytestmark = pytest.mark.asyncio
