"""Integration tests for LLM Service with real API calls.

These tests require actual API keys and are marked with @pytest.mark.integration.
They are skipped in CI if API keys are not configured.

To run these tests locally:
1. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in environment
2. Run: pytest tests/integration/test_llm_integration.py -v -m integration

Reference: docs/04_TEST_PLAN.md
"""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.services.llm import LLMService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_end_to_end_query() -> None:
    """Integration test: real OpenAI LLM API call."""
    settings = get_settings()

    # Skip if OpenAI not configured
    if settings.llm_provider != "openai" or not settings.openai_api_key:
        pytest.skip("OpenAI API key not configured")

    llm_service = LLMService()

    response = await llm_service.generate(
        prompt="What is 2+2? Answer with just the number.",
        system="You are a helpful math assistant.",
        temperature=0.0,
        max_tokens=10,
    )

    # Verify response is a string (not AgentFailure)
    assert isinstance(response, str)
    # Response should contain the answer
    assert "4" in response
    # Should be concise
    assert len(response) < 100


@pytest.mark.integration
@pytest.mark.asyncio
async def test_anthropic_end_to_end_query() -> None:
    """Integration test: real Anthropic LLM API call."""
    settings = get_settings()

    # Skip if Anthropic not configured
    if settings.llm_provider != "anthropic" or not settings.anthropic_api_key:
        pytest.skip("Anthropic API key not configured")

    llm_service = LLMService()

    response = await llm_service.generate(
        prompt="What is the capital of France? Answer with just the city name.",
        system="You are a helpful geography assistant.",
        temperature=0.0,
        max_tokens=10,
    )

    # Verify response is a string (not AgentFailure)
    assert isinstance(response, str)
    # Response should contain the answer
    assert "Paris" in response
    # Should be concise
    assert len(response) < 100


@pytest.mark.integration
@pytest.mark.asyncio
async def test_streaming_integration() -> None:
    """Integration test: real streaming LLM API call."""
    settings = get_settings()

    # Skip if no API key configured
    if settings.llm_provider == "openai" and not settings.openai_api_key:
        pytest.skip("OpenAI API key not configured")
    if settings.llm_provider == "anthropic" and not settings.anthropic_api_key:
        pytest.skip("Anthropic API key not configured")

    llm_service = LLMService()

    chunks: list[str] = []
    async for chunk in llm_service.stream_generate(
        prompt="Count from 1 to 3, separated by commas.",
        system="You are a helpful assistant.",
        temperature=0.0,
        max_tokens=50,
    ):
        chunks.append(chunk)

    # Verify we received chunks
    assert len(chunks) > 0
    # Combine chunks into full response
    full_response = "".join(chunks)
    assert len(full_response) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_citation_format_integration() -> None:
    """Integration test: verify LLM can generate proper citation format."""
    settings = get_settings()

    # Skip if no API key configured
    if settings.llm_provider == "openai" and not settings.openai_api_key:
        pytest.skip("OpenAI API key not configured")
    if settings.llm_provider == "anthropic" and not settings.anthropic_api_key:
        pytest.skip("Anthropic API key not configured")

    llm_service = LLMService()

    system_prompt = """You are a helpful assistant. When answering, cite sources using [1], [2] format.

Example:
Context:
[1] Paris is the capital of France.
[2] The Eiffel Tower is in Paris.

Question: Where is the Eiffel Tower?
Answer: The Eiffel Tower is in Paris [2], which is the capital of France [1]."""

    user_prompt = """Context:
[1] The Q3 cloud budget is $45,000.
[2] AWS spending increased 15% in Q3.

Question: What is the Q3 cloud budget?
Answer:"""

    response = await llm_service.generate(
        prompt=user_prompt,
        system=system_prompt,
        temperature=0.3,
        max_tokens=100,
    )

    # Verify response is a string
    assert isinstance(response, str)
    # Should contain citation markers
    assert "[1]" in response or "[2]" in response
    # Should mention the budget
    assert "45,000" in response or "45000" in response
