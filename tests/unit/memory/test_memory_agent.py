"""Memory Agent tests.

Reference: docs/04_TEST_PLAN.md Section 3.3
Test Class: TestMemoryAgent
"""

import pytest


class TestMemoryAgent:
    """Tests for the Memory Agent ("The Librarian")."""

    @pytest.mark.unit
    def test_retrieve_no_results(self) -> None:
        """Query with "Zorglub's exploits".

        Expect AgentFailure with code ERR_MEMORY_NO_RESULTS.
        """
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_exact_match_retrieval(self) -> None:
        """Seed DB with "The code is 1234". Query "What is the code?".

        Assert top result has score > 0.9 and matches text.
        """
        pytest.skip("Not implemented - P1-2")

    @pytest.mark.unit
    def test_metadata_filtering(self) -> None:
        """Query with filter={"source": "gdrive"}.

        Assert all returned chunks have source_type="gdrive".
        """
        pytest.skip("Not implemented - P1-2")
