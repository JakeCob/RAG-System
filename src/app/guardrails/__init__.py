"""Guardrails Agent - \"The Shield\".

Ensures safety and security for both incoming user requests and outgoing agent
responses. Acts as the gatekeeper against prompt injection, malicious payloads,
and PII leakage. Primary Task: UserRequest -> SafeRequest AND AgentResponse ->
SafeResponse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.schemas import AgentFailure, ErrorCodes, GuardrailsInput, GuardrailsOutput


if TYPE_CHECKING:
    from collections.abc import Sequence
    from re import Pattern

    from app.schemas.base import CheckType, RiskCategory


_PII_PLACEHOLDER = "[REDACTED:PII]"


@dataclass(slots=True)
class _DetectionResult:
    """Internal representation of a guardrail check outcome."""

    risk_category: RiskCategory | None
    reasoning: str
    sanitized_content: str
    pii_matches: list[str]


class GuardrailsAgent:
    """Lead security/guardrails agent providing prompt & PII protection."""

    def __init__(self, *, agent_id: str = "guardrails") -> None:
        self._agent_id = agent_id
        self._injection_patterns: tuple[Pattern[str], ...] = (
            re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
            re.compile(r"\bdo\s+anything\s+now\b", re.IGNORECASE),
            re.compile(r"\bDAN\b", re.IGNORECASE),
            re.compile(r"act\s+as\s+an?\s+unfiltered", re.IGNORECASE),
        )
        self._hate_keywords: tuple[str, ...] = (
            "exterminate",
            "kill all",
            "eradicate",
            "ethnic cleansing",
            "genocide",
        )
        self._malicious_patterns: tuple[Pattern[str], ...] = (
            re.compile(r"os\.system", re.IGNORECASE),
            re.compile(r"subprocess\.run", re.IGNORECASE),
            re.compile(r"rm\s+-rf\s+/", re.IGNORECASE),
            re.compile(r"bash\s+-c", re.IGNORECASE),
        )
        self._pii_patterns: tuple[Pattern[str], ...] = (
            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN
            re.compile(r"\bsk-[a-z0-9]{8,}\b", re.IGNORECASE),  # API token
            re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),  # Email
            re.compile(r"\b\d{16}\b"),  # Simplistic CC check
        )

    async def evaluate(self, payload: GuardrailsInput) -> GuardrailsOutput:
        """Return structured guardrail results for the provided payload."""

        detection = self._scan(payload)
        is_safe = self._is_safe(detection.risk_category, payload.check_type)

        return GuardrailsOutput(
            is_safe=is_safe,
            sanitized_content=detection.sanitized_content,
            risk_category=detection.risk_category,
            reasoning=detection.reasoning,
        )

    async def enforce(
        self, payload: GuardrailsInput
    ) -> GuardrailsOutput | AgentFailure:
        """Return sanitized content when safe, otherwise raise AgentFailure."""

        result = await self.evaluate(payload)
        if result.is_safe:
            return result

        error_code = (
            ErrorCodes.GUARDRAIL_INJECTION
            if result.risk_category == "injection"
            else ErrorCodes.GUARDRAIL_UNSAFE
        )
        message = (
            "Prompt injection detected; request blocked."
            if error_code == ErrorCodes.GUARDRAIL_INJECTION
            else "Unsafe content detected; guardrails blocked the payload."
        )

        return AgentFailure(
            agent_id=self._agent_id,
            error_code=error_code,
            message=message,
            details={
                "risk_category": result.risk_category,
                "reasoning": result.reasoning,
                "sanitized_content": result.sanitized_content,
            },
        )

    def _scan(self, payload: GuardrailsInput) -> _DetectionResult:
        """Evaluate the input for policy violations and return scan details."""

        content = payload.content
        sanitized_content, pii_matches = self._sanitize_pii(content)

        injection = self._match_any(content, self._injection_patterns)
        if injection:
            reasoning = f"Detected prompt-injection phrase: '{injection}'."
            return _DetectionResult(
                risk_category="injection",
                reasoning=reasoning,
                sanitized_content=sanitized_content,
                pii_matches=pii_matches,
            )

        hate = self._contains_keyword(content, self._hate_keywords)
        if hate:
            reasoning = f"Detected hate/toxicity keyword: '{hate}'."
            return _DetectionResult(
                risk_category="hate_speech",
                reasoning=reasoning,
                sanitized_content=sanitized_content,
                pii_matches=pii_matches,
            )

        malicious = self._match_any(content, self._malicious_patterns)
        if malicious:
            reasoning = f"Detected malicious code intent via '{malicious}'."
            return _DetectionResult(
                risk_category="malicious_code",
                reasoning=reasoning,
                sanitized_content=sanitized_content,
                pii_matches=pii_matches,
            )

        if pii_matches:
            reasoning = (
                f"Identified PII patterns ({len(pii_matches)} match(es)) "
                "and applied redaction."
            )
            return _DetectionResult(
                risk_category="pii",
                reasoning=reasoning,
                sanitized_content=sanitized_content,
                pii_matches=pii_matches,
            )

        return _DetectionResult(
            risk_category=None,
            reasoning="No guardrail violations detected.",
            sanitized_content=sanitized_content,
            pii_matches=pii_matches,
        )

    def _sanitize_pii(self, text: str) -> tuple[str, list[str]]:
        """Redact known PII patterns."""

        matches: list[str] = []
        sanitized = text

        for pattern in self._pii_patterns:

            def _replacer(match: re.Match[str]) -> str:
                matches.append(match.group(0))
                return _PII_PLACEHOLDER

            sanitized = pattern.sub(_replacer, sanitized)

        return sanitized, matches

    def _match_any(self, content: str, patterns: Sequence[Pattern[str]]) -> str | None:
        """Return the first regex match for the provided patterns."""

        for pattern in patterns:
            match = pattern.search(content)
            if match:
                return match.group(0)
        return None

    def _contains_keyword(self, content: str, keywords: Sequence[str]) -> str | None:
        """Return the first keyword found in the normalized content."""

        normalized = content.lower()
        for keyword in keywords:
            if keyword in normalized:
                return keyword
        return None

    def _is_safe(self, risk: RiskCategory | None, check_type: CheckType) -> bool:
        """Determine whether the payload passes guardrails."""

        if risk is None:
            return True
        if risk == "pii" and check_type == "input_validation":
            return True
        return False


__all__ = ["GuardrailsAgent"]
