"""End-to-End Integration tests.

Reference: docs/04_TEST_PLAN.md Section 7
Test File: tests/integration/test_end_to_end.py
"""

from __future__ import annotations

import pytest

from app.agents import ROMAOrchestrator
from app.exceptions import AgentFailureError
from app.ingestion import IngestionService
from app.memory import MemoryAgent
from app.schemas import ErrorCodes, MemoryQuery, QueryRequest, TailorOutput


class TestEndToEnd:
    """End-to-end smoke tests for the RAG pipeline.

    Flow: User Query -> Guardrails -> ROMA -> Memory -> Tailor -> Response
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_query_flow(self, tmp_path) -> None:
        """Test the complete query flow with a single ingested document."""

        memory = MemoryAgent(db_path=str(tmp_path / "test.lance"))
        ingestion = IngestionService(memory_agent=memory)
        await ingestion.ingest_document(
            content="Project Alpha is launching in May according to the roadmap.",
            filename="alpha.txt",
            source_id="alpha_launch_plan",
            source_type="gdrive",
            extra_metadata={"ingestion_source": "gdrive"},
        )

        orchestrator = ROMAOrchestrator(memory_agent=memory)
        result = await orchestrator.run_query(
            QueryRequest(text="When is Project Alpha launching?")
        )
        response = result.final_response

        assert isinstance(response, TailorOutput)
        assert "May" in response.content
        assert response.citations
        assert response.citations[0].source_id == "alpha_launch_plan"

        plan_descriptions = [step.description for step in result.execution_plan]
        assert any("Guardrails" in desc for desc in plan_descriptions)
        assert any("Retrieve context" in desc for desc in plan_descriptions)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multi_source_retrieval(self, tmp_path) -> None:
        """Test retrieval across multiple sources (GDrive + Web)."""

        memory = MemoryAgent(db_path=str(tmp_path / "test.lance"))
        ingestion = IngestionService(memory_agent=memory)
        await ingestion.ingest_document(
            content="Redwood compliance update: audits complete and new SOP active.",
            filename="compliance.txt",
            source_id="gdrive_compliance_doc",
            source_type="gdrive",
        )
        await ingestion.ingest_document(
            content="Status site timeline shows public maintenance every Friday.",
            filename="status.md",
            source_id="web_status_page",
            source_type="web",
            source_url="https://status.local/timeline",
        )

        orchestrator = ROMAOrchestrator(memory_agent=memory)
        result = await orchestrator.run_query(
            QueryRequest(
                text="Compare Redwood compliance update and status site timeline."
            )
        )

        source_ids = {
            citation.source_id for citation in result.final_response.citations
        }
        assert "gdrive_compliance_doc" in source_ids
        assert "web_status_page" in source_ids

        retrieve_steps = [
            step for step in result.execution_plan if "Retrieve" in step.description
        ]
        assert len(retrieve_steps) >= 2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_recovery_flow(self, tmp_path) -> None:
        """Test graceful handling when a source fails initially."""

        base_memory = MemoryAgent(db_path=str(tmp_path / "test.lance"))
        ingestion = IngestionService(memory_agent=base_memory)
        await ingestion.ingest_document(
            content="Phoenix playbook documents the May readiness review.",
            filename="phoenix.txt",
            source_id="phoenix_playbook",
            source_type="local",
        )

        class FlakyMemory:
            def __init__(self) -> None:
                self._delegate = base_memory
                self._should_fail = True

            async def query(self, query: MemoryQuery):
                if self._should_fail:
                    self._should_fail = False
                    raise AgentFailureError(
                        agent_id="memory.delegate",
                        error_code=ErrorCodes.MEMORY_NO_RESULTS,
                        message="Temporary LanceDB outage",
                        recoverable=True,
                    )
                return await self._delegate.query(query)

        orchestrator = ROMAOrchestrator(memory_agent=FlakyMemory())
        result = await orchestrator.run_query(
            QueryRequest(text="When is the Phoenix readiness review?")
        )

        response = result.final_response
        assert any(
            "Retry planning iteration" in step.description
            for step in result.execution_plan
        )
        assert "May" in response.content
