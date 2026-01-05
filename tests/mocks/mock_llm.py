"""Mock LLM client for testing.

Provides deterministic responses for testing RAG pipeline
without making actual API calls.
"""

from typing import Any


class MockLLMClient:
    """Mock LLM client that returns predefined responses."""

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        """Initialize with optional predefined responses.

        Args:
            responses: Mapping of input patterns to response strings.
        """
        self.responses = responses or {}
        self.call_history: list[dict[str, Any]] = []

    async def complete(self, prompt: str, **kwargs: Any) -> str:
        """Return a mock completion.

        Args:
            prompt: The input prompt.
            **kwargs: Additional arguments (ignored).

        Returns:
            A predefined or default response.
        """
        self.call_history.append({"prompt": prompt, "kwargs": kwargs})

        # Check for matching response
        for pattern, response in self.responses.items():
            if pattern in prompt:
                return response

        return f"[MOCK RESPONSE] Received prompt: {prompt[:50]}..."

    def reset(self) -> None:
        """Clear call history."""
        self.call_history = []
