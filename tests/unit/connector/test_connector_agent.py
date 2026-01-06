"""Connector Agent tests.

Reference: docs/04_TEST_PLAN.md Section 3.5
Test Class: TestConnectorAgent
"""

import os
import tempfile

import pytest

from app.schemas.connector import ConnectorOutput
from ingestion.connector import ConnectorAgent


class TestConnectorAgent:
    """Tests for the Connector Agent ("The Hand")."""

    @pytest.fixture
    def connector(self):
        return ConnectorAgent()

    @pytest.mark.unit
    def test_retry_logic_backoff(self) -> None:
        """Mock a 429/403 error from a URL.

        Assert the agent waits and retries (exponential backoff)
        before failing.
        """
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_gdrive_auth_refresh(self) -> None:
        """Mock a 401 error followed by a success.

        Assert the agent attempts to refresh the token
        and retries the request.
        """
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_user_agent_rotation(self) -> None:
        """Assert that subsequent requests (or retries) use different
        User-Agent headers if configured.
        """
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_local_file_ingestion(self, connector) -> None:
        """Simulate a file added to a watched directory.

        Assert the connector picks it up and returns the correct
        file_path and metadata.
        """
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as tmp:
            tmp.write("Test content")
            tmp_path = tmp.name

        try:
            # Act
            # Assuming process_file method
            result = connector.process_file(tmp_path, source_type="local")

            # Assert
            assert isinstance(result, ConnectorOutput)
            assert result.file_path == tmp_path
            assert result.file_size_bytes > 0
            assert result.checksum is not None
            assert "source_type" in result.source_metadata
            assert result.source_metadata["source_type"] == "local"

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
