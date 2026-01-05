"""Backend API tests.

Reference: docs/04_TEST_PLAN.md Section 4
Test Tool: TestClient (FastAPI)
"""

import pytest


class TestBackendAPI:
    """Backend API contract tests."""

    @pytest.mark.integration
    def test_api_health_check(self) -> None:
        """GET /health returns 200 OK.

        Expected response: {"db": "connected", "agents": "ready"}
        """
        pytest.skip("Not implemented - requires FastAPI app")

    @pytest.mark.integration
    def test_query_endpoint_valid(self) -> None:
        """POST /query with {"text": "Hello"} returns 200.

        Response structure must match TailoredResponse schema.
        """
        pytest.skip("Not implemented - requires FastAPI app")

    @pytest.mark.integration
    def test_query_streaming(self) -> None:
        """POST /query with stream=True returns SSE stream.

        Assert response is a generator/stream of chunks.
        """
        pytest.skip("Not implemented - requires FastAPI app")

    @pytest.mark.integration
    def test_ingest_upload_file(self) -> None:
        """POST /ingest with multipart PDF returns 202 Accepted.

        Response must include task_id for async processing.
        """
        pytest.skip("Not implemented - requires FastAPI app")

    @pytest.mark.integration
    def test_ingest_auth_middleware(self) -> None:
        """Request without Bearer Token returns 401 Unauthorized."""
        pytest.skip("Not implemented - requires FastAPI app")
