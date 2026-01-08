"""LLM Service Abstraction - Supports OpenAI and Anthropic APIs.

This module provides a unified async interface for LLM interactions with:
- Provider abstraction (OpenAI/Anthropic)
- Retry logic with exponential backoff
- Error handling with AgentFailure conversion
- Token tracking for cost analysis
- Streaming support

Reference: docs/02_AGENT_SPECS.md Section 4 (Error Codes)
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Literal, TypeVar, cast

import httpx
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.config import get_settings
from app.schemas import AgentFailure, ErrorCodes


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable, Callable


logger = logging.getLogger(__name__)
T = TypeVar("T")


class LLMService:
    """Unified LLM service supporting OpenAI and Anthropic providers.

    Provides async methods for text generation with automatic retry logic,
    error handling, and token tracking. All network errors are converted
    to AgentFailure objects with appropriate error codes.
    """

    def __init__(self) -> None:
        """Initialize LLM service with configured provider."""
        self._settings = get_settings()
        self._provider: Literal["openai", "anthropic"] = self._settings.llm_provider
        self._model = self._settings.llm_model
        self._max_retries = self._settings.llm_max_retries
        self._timeout = self._settings.llm_timeout_seconds
        self._client: AsyncOpenAI | AsyncAnthropic | None = None

        # Validate API keys
        if self._provider == "openai" and not self._settings.openai_api_key:
            raise ValueError(
                "OpenAI provider selected but OPENAI_API_KEY not configured"
            )
        if self._provider == "anthropic" and not self._settings.anthropic_api_key:
            raise ValueError(
                "Anthropic provider selected but ANTHROPIC_API_KEY not configured"
            )

    def _get_client(self) -> AsyncOpenAI | AsyncAnthropic:
        """Get or create the LLM client (lazy initialization with caching)."""
        if self._client is not None:
            return self._client

        if self._provider == "openai":
            self._client = AsyncOpenAI(
                api_key=self._settings.openai_api_key,
                timeout=httpx.Timeout(self._timeout, connect=10.0),
                max_retries=0,  # We handle retries ourselves
            )
        else:  # anthropic
            self._client = AsyncAnthropic(
                api_key=self._settings.anthropic_api_key,
                timeout=httpx.Timeout(self._timeout, connect=10.0),
                max_retries=0,  # We handle retries ourselves
            )

        assert self._client is not None
        return cast(AsyncOpenAI | AsyncAnthropic, self._client)

    def _get_openai_client(self) -> AsyncOpenAI:
        """Return the OpenAI client with an explicit type cast."""
        return cast(AsyncOpenAI, self._get_client())

    def _get_anthropic_client(self) -> AsyncAnthropic:
        """Return the Anthropic client with an explicit type cast."""
        return cast(AsyncAnthropic, self._get_client())

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str | AgentFailure:
        """Generate text from prompt using configured LLM provider.

        Args:
            prompt: User/assistant prompt text
            system: Optional system prompt (instructions for the model)
            temperature: Sampling temperature (0.0-2.0). Defaults to settings
            max_tokens: Max tokens to generate. Defaults to settings.

        Returns:
            Generated text string, or AgentFailure on error

        Example:
            response = await llm_service.generate(
                prompt="What is 2+2?",
                system="You are a helpful math assistant.",
                temperature=0.0
            )
        """
        temp = (
            temperature if temperature is not None else self._settings.llm_temperature
        )
        tokens = max_tokens if max_tokens is not None else self._settings.llm_max_tokens

        async def _call() -> str:
            if self._provider == "openai":
                return await self._generate_openai(prompt, system, temp, tokens)
            return await self._generate_anthropic(prompt, system, temp, tokens)

        try:
            return await self._retry_with_backoff(_call)
        except httpx.TimeoutException as exc:
            logger.error(
                "LLM request timeout",
                extra={
                    "agent_id": "llm_service",
                    "provider": self._provider,
                    "timeout_seconds": self._timeout,
                },
            )
            return AgentFailure(
                agent_id="llm_service",
                error_code=ErrorCodes.TIMEOUT,
                message=f"LLM request timed out after {self._timeout}s",
                recoverable=True,
                details={"provider": self._provider, "error": str(exc)},
            )
        except httpx.HTTPStatusError as exc:
            return self._handle_http_error(exc)
        except Exception as exc:
            logger.exception(
                "Unexpected LLM error",
                extra={"agent_id": "llm_service", "provider": self._provider},
            )
            return AgentFailure(
                agent_id="llm_service",
                error_code=ErrorCodes.TIMEOUT,
                message=f"Unexpected LLM error: {type(exc).__name__}",
                recoverable=False,
                details={"error": str(exc)},
            )

    async def stream_generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream generated text chunks from LLM.

        Args:
            prompt: User/assistant prompt text
            system: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Yields:
            Text chunks as they are generated

        Example:
            async for chunk in llm_service.stream_generate(prompt="Hi"):
                print(chunk, end="", flush=True)
        """
        temp = (
            temperature if temperature is not None else self._settings.llm_temperature
        )
        tokens = max_tokens if max_tokens is not None else self._settings.llm_max_tokens

        if self._provider == "openai":
            async for chunk in self._stream_openai(prompt, system, temp, tokens):
                yield chunk
        else:
            async for chunk in self._stream_anthropic(prompt, system, temp, tokens):
                yield chunk

    async def count_tokens(self, text: str) -> int:
        """Estimate token count for text (approximate).

        Uses simple heuristic: ~4 characters per token.
        For production, consider using tiktoken (OpenAI) or similar.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Simple approximation: 1 token ≈ 4 characters
        # More accurate would be tiktoken for OpenAI or specific tokenizer
        return max(1, len(text) // 4)

    async def _generate_openai(
        self,
        prompt: str,
        system: str | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Generate text using OpenAI API."""
        client = self._get_openai_client()

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        logger.info(
            "OpenAI API call",
            extra={
                "agent_id": "llm_service",
                "model": self._model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "input_tokens_est": await self.count_tokens(prompt),
            },
        )

        response = await client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content or ""

        # Log token usage
        if response.usage:
            logger.info(
                "OpenAI token usage",
                extra={
                    "agent_id": "llm_service",
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            )

        return content

    async def _generate_anthropic(
        self,
        prompt: str,
        system: str | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Generate text using Anthropic API."""
        client = self._get_anthropic_client()

        logger.info(
            "Anthropic API call",
            extra={
                "agent_id": "llm_service",
                "model": self._model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "input_tokens_est": await self.count_tokens(prompt),
            },
        )

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            kwargs["system"] = system

        response = await client.messages.create(**kwargs)

        # Extract text from response
        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        # Log token usage
        logger.info(
            "Anthropic token usage",
            extra={
                "agent_id": "llm_service",
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

        return content

    async def _stream_openai(
        self,
        prompt: str,
        system: str | None,
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Stream text chunks from OpenAI API."""
        client = self._get_openai_client()

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in response:  # type: ignore[union-attr]
            content = chunk.choices[0].delta.content
            if content:
                yield content

    async def _stream_anthropic(
        self,
        prompt: str,
        system: str | None,
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Stream text chunks from Anthropic API."""
        client = self._get_anthropic_client()

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            kwargs["system"] = system

        async with client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    async def _retry_with_backoff(
        self,
        func: Callable[[], Awaitable[T]],
        initial_delay: float = 1.0,
        max_delay: float = 16.0,
        backoff_factor: float = 2.0,
    ) -> T:
        """Retry function with exponential backoff on rate limits.

        Args:
            func: Async function to retry
            initial_delay: Initial delay in seconds (default: 1.0)
            max_delay: Maximum delay in seconds (default: 16.0)
            backoff_factor: Multiplier for delay after each retry (default: 2.0)

        Returns:
            Result of successful function call

        Raises:
            httpx.HTTPStatusError: If max retries exceeded or non-retryable error
            httpx.TimeoutException: If request times out
        """
        delay = initial_delay

        for attempt in range(self._max_retries):
            try:
                return await func()
            except httpx.HTTPStatusError as exc:
                # Only retry on 429 (rate limit) or 5xx (server errors)
                status = exc.response.status_code
                is_rate_limit = status == 429
                is_server_error = 500 <= status < 600
                is_last_attempt = attempt >= self._max_retries - 1

                if (is_rate_limit or is_server_error) and not is_last_attempt:
                    logger.warning(
                        "LLM request failed, retrying",
                        extra={
                            "agent_id": "llm_service",
                            "provider": self._provider,
                            "status_code": status,
                            "retry_count": attempt + 1,
                            "delay_seconds": min(delay, max_delay),
                        },
                    )
                    await asyncio.sleep(min(delay, max_delay))
                    delay *= backoff_factor
                else:
                    # Non-retryable error or last attempt
                    raise

        # This should never be reached due to the raise in the loop
        raise RuntimeError("Max retries exceeded")

    def _handle_http_error(self, exc: httpx.HTTPStatusError) -> AgentFailure:
        """Convert HTTP errors to AgentFailure objects."""
        status = exc.response.status_code

        # Authentication errors (401, 403)
        if status in (401, 403):
            logger.error(
                "LLM authentication failed",
                extra={
                    "agent_id": "llm_service",
                    "provider": self._provider,
                    "status_code": status,
                },
            )
            return AgentFailure(
                agent_id="llm_service",
                error_code=ErrorCodes.CONNECTOR_AUTH,
                message="Invalid LLM API key or insufficient permissions",
                recoverable=False,
                details={"provider": self._provider, "status_code": status},
            )

        # Rate limit (429) - should not reach here due to retry logic
        if status == 429:
            return AgentFailure(
                agent_id="llm_service",
                error_code=ErrorCodes.TIMEOUT,
                message="LLM rate limit exceeded after retries",
                recoverable=True,
                details={"provider": self._provider, "status_code": status},
            )

        # Server errors (5xx)
        if 500 <= status < 600:
            return AgentFailure(
                agent_id="llm_service",
                error_code=ErrorCodes.TIMEOUT,
                message=f"LLM server error: {status}",
                recoverable=True,
                details={"provider": self._provider, "status_code": status},
            )

        # Other client errors (4xx)
        return AgentFailure(
            agent_id="llm_service",
            error_code=ErrorCodes.TIMEOUT,
            message=f"LLM client error: {status}",
            recoverable=False,
            details={
                "provider": self._provider,
                "status_code": status,
                "response": exc.response.text[:500],
            },
        )


__all__ = ["LLMService"]
