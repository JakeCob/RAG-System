"""Application-specific exception helpers."""

from __future__ import annotations

from typing import Any

from app.schemas import AgentFailure


class AgentFailureError(RuntimeError):
    """Raised when an agent cannot complete its task."""

    def __init__(
        self,
        *,
        agent_id: str,
        error_code: str,
        message: str,
        recoverable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.failure = AgentFailure(
            agent_id=agent_id,
            error_code=error_code,
            message=message,
            recoverable=recoverable,
            details=details,
        )

    def __str__(self) -> str:
        """Return a human-readable form for logging."""

        return f"{self.failure.agent_id}::{self.failure.error_code} - {self.failure.message}"


__all__ = ["AgentFailureError"]

