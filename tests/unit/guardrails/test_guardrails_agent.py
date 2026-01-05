"""Guardrails Agent tests.

Reference: docs/04_TEST_PLAN.md Section 3.2
Test Class: TestGuardrailsAgent
"""

import pytest


class TestGuardrailsAgent:
    """Tests for the Guardrails Agent ("The Shield")."""

    @pytest.mark.unit
    def test_detect_pii(self) -> None:
        """Input text containing a fake SSN or API key (e.g., sk-12345).

        Assert risk_category="pii" and content is redacted or flagged.
        """
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_detect_toxicity(self) -> None:
        """Input hate speech or toxic prompts.

        Assert is_safe=False and risk_category="hate_speech".
        """
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_advanced_jailbreak(self) -> None:
        """Input a "DAN" (Do Anything Now) style prompt.

        Assert is_safe=False and risk_category="injection".
        """
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_malicious_payload(self) -> None:
        """Input a prompt trying to execute Python code/system commands.

        Assert refusal.
        """
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_output_safety_redaction(self) -> None:
        """Input a generated response containing a mock API key.

        Assert check_type="output_safety" catches and redacts it.
        """
        pytest.skip("Not implemented - P1-2")
