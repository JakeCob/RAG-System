"""Guardrails Agent schemas.

Reference: docs/02_AGENT_SPECS.md Section 2.0
"""

from typing import Any

from pydantic import BaseModel

from app.schemas.base import CheckType, RiskCategory


class GuardrailsInput(BaseModel):
    """Input for the Guardrails Agent."""

    content: str
    check_type: CheckType
    metadata: dict[str, Any] | None = None


class GuardrailsOutput(BaseModel):
    """Output from the Guardrails Agent."""

    is_safe: bool
    sanitized_content: str
    risk_category: RiskCategory | None
    reasoning: str
