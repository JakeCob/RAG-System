"""Backend API tests.

Reference: docs/04_TEST_PLAN.md Section 4
Test Tool: TestClient (FastAPI)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import _get_ingestion_service, app


if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@pytest.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    """Provide an Httpx AsyncClient wired to the FastAPI ASGI app."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        ingestion_service = _get_ingestion_service()
        await ingestion_service.ingest_document(
            content="Seed document for API query tests.",
            filename="seed.txt",
            source_id="seed_doc",
            source_type="local",
        )
        yield client


def _build_multipart_body(
    filename: str, data: bytes, content_type: str
) -> tuple[str, bytes]:
    """Construct a minimal multipart/form-data payload for UploadFile."""

    boundary = "----pytestboundary"
    payload = data.decode("latin1")
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
        f"{payload}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    return boundary, body


class TestBackendAPI:
    """Backend API contract tests."""

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_api_health_check(self, async_client: AsyncClient) -> None:
        """GET /health returns 200 OK."""

        response = await async_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"db": "connected", "agents": "ready"}

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_memory_status(self, async_client: AsyncClient) -> None:
        """GET /memory/status returns indexed chunk count."""

        response = await async_client.get("/memory/status")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body.get("chunk_count"), int)
        assert body["chunk_count"] >= 1

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_query_endpoint_valid(self, async_client: AsyncClient) -> None:
        """POST /query with {"text": "Hello"} returns TailorOutput payload."""

        response = await async_client.post("/query", json={"text": "Hello"})
        assert response.status_code == 200
        body = response.json()

        # TailorOutput fields
        assert body["tone_used"] == "General"
        assert isinstance(body["confidence_score"], float)
        assert isinstance(body["content"], str) and body["content"]
        assert isinstance(body["follow_up_suggestions"], list)

        citations = body["citations"]
        assert isinstance(citations, list) and citations
        first = citations[0]
        assert {"source_id", "chunk_id", "text_snippet"}.issubset(first.keys())

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_query_streaming(self, async_client: AsyncClient) -> None:
        """POST /query with stream=True returns SSE stream."""

        async with async_client.stream(
            "POST", "/query", json={"text": "Stream me", "stream": True}
        ) as response:
            assert response.status_code == 200

            token_events: list[str] = []
            complete_event: str | None = None
            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith("event: token"):
                    token_events.append(line)
                if line.startswith("event: complete"):
                    complete_event = line
                    break

            assert token_events, "Expected at least one streamed token event."
            assert complete_event is not None, "Expected terminal complete event."

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_ingest_upload_file(self, async_client: AsyncClient) -> None:
        """POST /ingest with multipart text returns 202 Accepted."""

        boundary, body = _build_multipart_body(
            filename="example.txt",
            data=b"Example ingestion text",
            content_type="text/plain",
        )
        headers = {
            "Authorization": "Bearer local-dev-token",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        response = await async_client.post("/ingest", content=body, headers=headers)

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "queued"
        assert body["filename"] == "example.txt"
        assert body["task_id"]

    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_ingest_auth_middleware(self, async_client: AsyncClient) -> None:
        """Request without Bearer Token returns 401 Unauthorized."""

        boundary, body = _build_multipart_body(
            filename="example.txt",
            data=b"Example ingestion text",
            content_type="text/plain",
        )
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        response = await async_client.post("/ingest", content=body, headers=headers)

        assert response.status_code == 401
        detail = response.json()["detail"]
        assert detail["error_code"] == "ERR_CONNECTOR_AUTH"
