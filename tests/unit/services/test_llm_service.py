"""Unit tests for LLM Service.

Tests cover:
- OpenAI and Anthropic provider integration
- Retry logic with exponential backoff
- Error handling (auth, timeout, rate limits)
- Token counting
- Streaming support

Reference: docs/04_TEST_PLAN.md Section 3.7
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest
from anthropic.types import ContentBlock, Message, TextBlock, Usage
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from app.schemas import AgentFailure, ErrorCodes
from app.services.llm import LLMService


@pytest.mark.unit
class TestLLMService:
    """Test suite for LLMService class."""

    @pytest.mark.asyncio
    async def test_openai_generate_success(self) -> None:
        """Test successful OpenAI API call returns text."""
        with patch("app.services.llm.get_settings") as mock_settings:
            # Configure settings
            settings = Mock()
            settings.llm_provider = "openai"
            settings.llm_model = "gpt-4o"
            settings.openai_api_key = "test-key"
            settings.anthropic_api_key = ""
            settings.llm_max_retries = 3
            settings.llm_timeout_seconds = 30
            settings.llm_temperature = 0.7
            settings.llm_max_tokens = 2048
            mock_settings.return_value = settings

            # Mock OpenAI client
            mock_completion = ChatCompletion(
                id="test-id",
                object="chat.completion",
                created=1234567890,
                model="gpt-4o",
                choices=[
                    Choice(
                        index=0,
                        message=ChatCompletionMessage(
                            role="assistant", content="Test response"
                        ),
                        finish_reason="stop",
                    )
                ],
                usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            )

            with patch("app.services.llm.AsyncOpenAI") as mock_openai_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = AsyncMock(
                    return_value=mock_completion
                )
                mock_openai_class.return_value = mock_client

                service = LLMService()
                result = await service.generate(
                    prompt="Test prompt", system="Test system", temperature=0.5
                )

                assert isinstance(result, str)
                assert result == "Test response"
                mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_anthropic_generate_success(self) -> None:
        """Test successful Anthropic API call returns text."""
        with patch("app.services.llm.get_settings") as mock_settings:
            # Configure settings
            settings = Mock()
            settings.llm_provider = "anthropic"
            settings.llm_model = "claude-sonnet-3.5"
            settings.openai_api_key = ""
            settings.anthropic_api_key = "test-key"
            settings.llm_max_retries = 3
            settings.llm_timeout_seconds = 30
            settings.llm_temperature = 0.7
            settings.llm_max_tokens = 2048
            mock_settings.return_value = settings

            # Mock Anthropic response
            mock_response = Message(
                id="test-id",
                type="message",
                role="assistant",
                content=[TextBlock(type="text", text="Anthropic test response")],
                model="claude-sonnet-3.5",
                stop_reason="end_turn",
                stop_sequence=None,
                usage=Usage(input_tokens=10, output_tokens=5),
            )

            with patch("app.services.llm.AsyncAnthropic") as mock_anthropic_class:
                mock_client = AsyncMock()
                mock_client.messages.create = AsyncMock(return_value=mock_response)
                mock_anthropic_class.return_value = mock_client

                service = LLMService()
                result = await service.generate(
                    prompt="Test prompt", system="Test system"
                )

                assert isinstance(result, str)
                assert result == "Anthropic test response"
                mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_retry(self) -> None:
        """Test 429 error triggers exponential backoff and retry."""
        with patch("app.services.llm.get_settings") as mock_settings:
            # Configure settings
            settings = Mock()
            settings.llm_provider = "openai"
            settings.llm_model = "gpt-4o"
            settings.openai_api_key = "test-key"
            settings.anthropic_api_key = ""
            settings.llm_max_retries = 3
            settings.llm_timeout_seconds = 30
            settings.llm_temperature = 0.7
            settings.llm_max_tokens = 2048
            mock_settings.return_value = settings

            # First call raises 429, second succeeds
            mock_completion = ChatCompletion(
                id="test-id",
                object="chat.completion",
                created=1234567890,
                model="gpt-4o",
                choices=[
                    Choice(
                        index=0,
                        message=ChatCompletionMessage(
                            role="assistant", content="Success after retry"
                        ),
                        finish_reason="stop",
                    )
                ],
                usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            )

            with patch("app.services.llm.AsyncOpenAI") as mock_openai_class:
                mock_client = AsyncMock()
                # First call raises 429, second succeeds
                mock_response_429 = Mock(spec=httpx.Response)
                mock_response_429.status_code = 429
                mock_response_429.text = "Rate limit exceeded"

                mock_client.chat.completions.create = AsyncMock(
                    side_effect=[
                        httpx.HTTPStatusError(
                            "Rate limit",
                            request=Mock(),
                            response=mock_response_429,
                        ),
                        mock_completion,
                    ]
                )
                mock_openai_class.return_value = mock_client

                with patch("asyncio.sleep") as mock_sleep:
                    service = LLMService()
                    result = await service.generate(prompt="Test prompt")

                    assert isinstance(result, str)
                    assert result == "Success after retry"
                    # Verify retry occurred with delay
                    mock_sleep.assert_called_once()
                    assert mock_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_invalid_api_key(self) -> None:
        """Test 401 error returns AgentFailure with CONNECTOR_AUTH code."""
        with patch("app.services.llm.get_settings") as mock_settings:
            # Configure settings
            settings = Mock()
            settings.llm_provider = "openai"
            settings.llm_model = "gpt-4o"
            settings.openai_api_key = "invalid-key"
            settings.anthropic_api_key = ""
            settings.llm_max_retries = 3
            settings.llm_timeout_seconds = 30
            settings.llm_temperature = 0.7
            settings.llm_max_tokens = 2048
            mock_settings.return_value = settings

            with patch("app.services.llm.AsyncOpenAI") as mock_openai_class:
                mock_client = AsyncMock()
                mock_response_401 = Mock(spec=httpx.Response)
                mock_response_401.status_code = 401
                mock_response_401.text = "Invalid API key"

                mock_client.chat.completions.create = AsyncMock(
                    side_effect=httpx.HTTPStatusError(
                        "Auth failed",
                        request=Mock(),
                        response=mock_response_401,
                    )
                )
                mock_openai_class.return_value = mock_client

                service = LLMService()
                result = await service.generate(prompt="Test prompt")

                assert isinstance(result, AgentFailure)
                assert result.error_code == ErrorCodes.CONNECTOR_AUTH
                assert result.recoverable is False
                assert "Invalid LLM API key" in result.message

    @pytest.mark.asyncio
    async def test_timeout_error(self) -> None:
        """Test timeout returns AgentFailure with TIMEOUT code."""
        with patch("app.services.llm.get_settings") as mock_settings:
            # Configure settings
            settings = Mock()
            settings.llm_provider = "openai"
            settings.llm_model = "gpt-4o"
            settings.openai_api_key = "test-key"
            settings.anthropic_api_key = ""
            settings.llm_max_retries = 3
            settings.llm_timeout_seconds = 30
            settings.llm_temperature = 0.7
            settings.llm_max_tokens = 2048
            mock_settings.return_value = settings

            with patch("app.services.llm.AsyncOpenAI") as mock_openai_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = AsyncMock(
                    side_effect=httpx.TimeoutException("Request timeout")
                )
                mock_openai_class.return_value = mock_client

                service = LLMService()
                result = await service.generate(prompt="Test prompt")

                assert isinstance(result, AgentFailure)
                assert result.error_code == ErrorCodes.TIMEOUT
                assert result.recoverable is True
                assert "timed out" in result.message.lower()

    @pytest.mark.asyncio
    async def test_stream_generate_yields_chunks(self) -> None:
        """Test streaming returns async generator of text chunks."""
        with patch("app.services.llm.get_settings") as mock_settings:
            # Configure settings
            settings = Mock()
            settings.llm_provider = "openai"
            settings.llm_model = "gpt-4o"
            settings.openai_api_key = "test-key"
            settings.anthropic_api_key = ""
            settings.llm_max_retries = 3
            settings.llm_timeout_seconds = 30
            settings.llm_temperature = 0.7
            settings.llm_max_tokens = 2048
            mock_settings.return_value = settings

            # Create mock streaming response
            async def mock_stream() -> AsyncMock:
                chunks = [
                    Mock(choices=[Mock(delta=Mock(content="Hello"))]),
                    Mock(choices=[Mock(delta=Mock(content=" world"))]),
                    Mock(choices=[Mock(delta=Mock(content=None))]),  # End marker
                ]
                for chunk in chunks:
                    yield chunk

            with patch("app.services.llm.AsyncOpenAI") as mock_openai_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = AsyncMock(
                    return_value=mock_stream()
                )
                mock_openai_class.return_value = mock_client

                service = LLMService()
                chunks: list[str] = []

                async for chunk in service.stream_generate(prompt="Test prompt"):
                    chunks.append(chunk)

                assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_token_counting(self) -> None:
        """Test count_tokens returns reasonable estimate."""
        with patch("app.services.llm.get_settings") as mock_settings:
            # Configure settings
            settings = Mock()
            settings.llm_provider = "openai"
            settings.llm_model = "gpt-4o"
            settings.openai_api_key = "test-key"
            settings.anthropic_api_key = ""
            settings.llm_max_retries = 3
            settings.llm_timeout_seconds = 30
            settings.llm_temperature = 0.7
            settings.llm_max_tokens = 2048
            mock_settings.return_value = settings

            service = LLMService()

            # Test various text lengths
            short_text = "Hello, world!"
            count = await service.count_tokens(short_text)
            assert count > 0
            assert count <= len(short_text)  # Should be less than character count

            long_text = "This is a much longer text " * 100
            long_count = await service.count_tokens(long_text)
            assert long_count > count  # Longer text should have more tokens

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self) -> None:
        """Test failing after max retries returns AgentFailure."""
        with patch("app.services.llm.get_settings") as mock_settings:
            # Configure settings
            settings = Mock()
            settings.llm_provider = "openai"
            settings.llm_model = "gpt-4o"
            settings.openai_api_key = "test-key"
            settings.anthropic_api_key = ""
            settings.llm_max_retries = 2  # Only 2 retries for faster test
            settings.llm_timeout_seconds = 30
            settings.llm_temperature = 0.7
            settings.llm_max_tokens = 2048
            mock_settings.return_value = settings

            with patch("app.services.llm.AsyncOpenAI") as mock_openai_class:
                mock_client = AsyncMock()
                mock_response_500 = Mock(spec=httpx.Response)
                mock_response_500.status_code = 500
                mock_response_500.text = "Internal server error"

                # Always raise 500 error
                mock_client.chat.completions.create = AsyncMock(
                    side_effect=httpx.HTTPStatusError(
                        "Server error",
                        request=Mock(),
                        response=mock_response_500,
                    )
                )
                mock_openai_class.return_value = mock_client

                with patch("asyncio.sleep"):
                    service = LLMService()
                    result = await service.generate(prompt="Test prompt")

                    assert isinstance(result, AgentFailure)
                    assert result.error_code == ErrorCodes.TIMEOUT
                    assert result.recoverable is True
                    # Verify all retries were exhausted (initial + 2 retries = 2 total calls)
                    assert mock_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_server_error_retry(self) -> None:
        """Test 5xx server errors trigger retry logic."""
        with patch("app.services.llm.get_settings") as mock_settings:
            # Configure settings
            settings = Mock()
            settings.llm_provider = "openai"
            settings.llm_model = "gpt-4o"
            settings.openai_api_key = "test-key"
            settings.anthropic_api_key = ""
            settings.llm_max_retries = 3
            settings.llm_timeout_seconds = 30
            settings.llm_temperature = 0.7
            settings.llm_max_tokens = 2048
            mock_settings.return_value = settings

            # First call raises 503, second succeeds
            mock_completion = ChatCompletion(
                id="test-id",
                object="chat.completion",
                created=1234567890,
                model="gpt-4o",
                choices=[
                    Choice(
                        index=0,
                        message=ChatCompletionMessage(
                            role="assistant", content="Success after server error"
                        ),
                        finish_reason="stop",
                    )
                ],
                usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            )

            with patch("app.services.llm.AsyncOpenAI") as mock_openai_class:
                mock_client = AsyncMock()
                mock_response_503 = Mock(spec=httpx.Response)
                mock_response_503.status_code = 503
                mock_response_503.text = "Service unavailable"

                mock_client.chat.completions.create = AsyncMock(
                    side_effect=[
                        httpx.HTTPStatusError(
                            "Service unavailable",
                            request=Mock(),
                            response=mock_response_503,
                        ),
                        mock_completion,
                    ]
                )
                mock_openai_class.return_value = mock_client

                with patch("asyncio.sleep") as mock_sleep:
                    service = LLMService()
                    result = await service.generate(prompt="Test prompt")

                    assert isinstance(result, str)
                    assert result == "Success after server error"
                    # Verify retry occurred
                    mock_sleep.assert_called_once()
                    assert mock_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_client_error(self) -> None:
        """Test 4xx client errors (except 429) don't retry."""
        with patch("app.services.llm.get_settings") as mock_settings:
            # Configure settings
            settings = Mock()
            settings.llm_provider = "openai"
            settings.llm_model = "gpt-4o"
            settings.openai_api_key = "test-key"
            settings.anthropic_api_key = ""
            settings.llm_max_retries = 3
            settings.llm_timeout_seconds = 30
            settings.llm_temperature = 0.7
            settings.llm_max_tokens = 2048
            mock_settings.return_value = settings

            with patch("app.services.llm.AsyncOpenAI") as mock_openai_class:
                mock_client = AsyncMock()
                mock_response_400 = Mock(spec=httpx.Response)
                mock_response_400.status_code = 400
                mock_response_400.text = "Bad request"

                mock_client.chat.completions.create = AsyncMock(
                    side_effect=httpx.HTTPStatusError(
                        "Bad request",
                        request=Mock(),
                        response=mock_response_400,
                    )
                )
                mock_openai_class.return_value = mock_client

                service = LLMService()
                result = await service.generate(prompt="Test prompt")

                assert isinstance(result, AgentFailure)
                assert result.error_code == ErrorCodes.TIMEOUT
                assert result.recoverable is False
                # Should not retry for 400 error
                assert mock_client.chat.completions.create.call_count == 1
