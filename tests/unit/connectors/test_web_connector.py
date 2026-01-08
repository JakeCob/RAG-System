"""Unit tests for web connector."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.connectors.web import WebConnector
from app.schemas import AgentFailure, ErrorCodes


class TestWebConnector:
    """Test suite for web scraping connector."""

    @pytest.mark.unit
    @patch("app.connectors.web.httpx.AsyncClient")
    @patch("app.connectors.web.trafilatura.extract")
    async def test_fetch_success(self, mock_extract, mock_client):
        """Test successful web page fetch and extraction."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>Test content</p></body></html>"

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Mock trafilatura extraction
        mock_extract.return_value = (
            "# Test Page\n\nThis is a test page with enough content to pass "
            "the validation. Test content"
        )

        connector = WebConnector()
        result = await connector.fetch("https://example.com/article")

        assert not isinstance(result, AgentFailure)
        markdown, metadata = result
        assert "Test content" in markdown
        assert metadata["url"] == "https://example.com/article"
        assert "content_hash" in metadata

    @pytest.mark.unit
    @patch("app.connectors.web.httpx.AsyncClient")
    async def test_fetch_404_not_found(self, mock_client):
        """Test 404 error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        connector = WebConnector()
        result = await connector.fetch("https://example.com/missing")

        assert isinstance(result, AgentFailure)
        assert result.error_code == ErrorCodes.CONNECTOR_NOT_FOUND
        assert "not found" in result.message.lower()

    @pytest.mark.unit
    @patch("app.connectors.web.httpx.AsyncClient")
    async def test_fetch_403_forbidden(self, mock_client):
        """Test 403 access denied handling."""
        mock_response = MagicMock()
        mock_response.status_code = 403

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        connector = WebConnector()
        result = await connector.fetch("https://example.com/forbidden")

        assert isinstance(result, AgentFailure)
        assert result.error_code == ErrorCodes.CONNECTOR_AUTH
        assert "403" in result.message

    @pytest.mark.unit
    @patch("app.connectors.web.httpx.AsyncClient")
    async def test_rate_limit_retry(self, mock_client):
        """Test exponential backoff on 429 rate limit."""
        # First 2 attempts return 429, third succeeds
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.text = "<html><body>Success</body></html>"

        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = [
            mock_response_429,
            mock_response_429,
            mock_response_200,
        ]
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with patch("app.connectors.web.trafilatura.extract") as mock_extract:
            mock_extract.return_value = (
                "Success content that is long enough to pass the validation."
            )

            connector = WebConnector(max_retries=5)
            result = await connector.fetch("https://example.com/rate-limited")

            # Should eventually succeed after retries
            assert not isinstance(result, AgentFailure)
            assert mock_client_instance.get.call_count == 3

    @pytest.mark.unit
    @patch("app.connectors.web.httpx.AsyncClient")
    async def test_network_timeout(self, mock_client):
        """Test network timeout handling."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = httpx.TimeoutException("Timeout")
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        connector = WebConnector(max_retries=3, timeout=5)
        result = await connector.fetch("https://slow-site.com")

        assert isinstance(result, AgentFailure)
        assert result.error_code == ErrorCodes.CONNECTOR_NETWORK
        assert (
            "timeout" in result.message.lower() or "network" in result.message.lower()
        )

    @pytest.mark.unit
    @patch("app.connectors.web.WebConnector._fetch_with_retry", new_callable=AsyncMock)
    async def test_blocked_domain(self, mock_fetch):
        """Test domain whitelist enforcement."""
        mock_fetch.return_value = "<html></html>"
        connector = WebConnector(allowed_domains=["example.com", "docs.python.org"])

        # This should now use the mocked fetch, not a real network call
        await connector.fetch("https://example.com/page")

        # Blocked domain
        result_blocked = await connector.fetch("https://malicious-site.com/page")
        assert isinstance(result_blocked, AgentFailure)
        assert result_blocked.error_code == ErrorCodes.CONNECTOR_BLOCKED_DOMAIN

        # Ensure fetch was not called for the blocked domain
        # This requires checking the calls to the mock
        assert mock_fetch.call_count == 1
        mock_fetch.assert_called_once_with("https://example.com/page")

    @pytest.mark.unit
    @patch("app.connectors.web.httpx.AsyncClient")
    @patch("app.connectors.web.trafilatura.extract")
    async def test_empty_content_handling(self, mock_extract, mock_client):
        """Test handling of pages with no extractable content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><nav>Navigation only</nav></html>"

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # trafilatura returns None or very short content
        mock_extract.return_value = "X"  # Too short (<50 chars)

        connector = WebConnector()
        result = await connector.fetch("https://example.com/empty")

        assert isinstance(result, AgentFailure)
        assert result.error_code == ErrorCodes.CONNECTOR_INVALID_CONTENT

    @pytest.mark.unit
    def test_user_agent_rotation(self):
        """Test User-Agent header rotation."""
        connector = WebConnector(user_agents=["Agent1", "Agent2", "Agent3"])

        agents = [connector._get_user_agent() for _ in range(6)]

        # Should cycle through agents
        assert agents == ["Agent1", "Agent2", "Agent3", "Agent1", "Agent2", "Agent3"]

    @pytest.mark.unit
    @patch("app.connectors.web.httpx.AsyncClient")
    @patch("app.connectors.web.trafilatura.extract")
    @patch("app.connectors.web.trafilatura.extract_metadata")
    async def test_metadata_extraction(self, mock_meta, mock_extract, mock_client):
        """Test extraction of page metadata (title, author, date)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><head><title>Test Article</title></head></html>"

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        mock_extract.return_value = (
            "Article content here with enough text to pass the validation."
        )

        # Mock metadata
        mock_meta_obj = MagicMock()
        mock_meta_obj.title = "Test Article"
        mock_meta_obj.author = "John Doe"
        mock_meta_obj.date = "2025-01-01"
        mock_meta_obj.description = "Test description"
        mock_meta_obj.sitename = "Example Site"
        mock_meta.return_value = mock_meta_obj

        connector = WebConnector()
        result = await connector.fetch(
            "https://example.com/article", extract_metadata=True
        )

        assert not isinstance(result, AgentFailure)
        _markdown, metadata = result
        assert metadata["title"] == "Test Article"
        assert metadata["author"] == "John Doe"
        assert metadata["date"] == "2025-01-01"
