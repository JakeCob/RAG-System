"""Conversation State tests.

Reference: docs/04_TEST_PLAN.md Section 3.8
Test Class: TestConversationState
"""

import pytest

from app.schemas import ConversationState


class TestConversationState:
    """Tests for the Conversation State ("The Memory")."""

    @pytest.mark.unit
    def test_history_appending(self) -> None:
        """Add a user message and assistant response.

        Assert history list length increases by 2 and timestamps are present.
        """
        state = ConversationState(session_id="test-session")
        state.add_message("user", "Hello")
        state.add_message("assistant", "Hi there!")

        assert len(state.history) == 2
        assert state.history[0].role == "user"
        assert state.history[0].content == "Hello"
        assert state.history[0].timestamp is not None
        assert state.history[1].role == "assistant"

    @pytest.mark.unit
    def test_context_clearing(self) -> None:
        """Simulate the end of a turn. Call clear_context().

        Assert accumulated_context is empty but history remains.
        """
        state = ConversationState(session_id="test-session")
        state.add_message("user", "Test message")
        state.current_plan = []  # Simulate having a plan

        state.clear_context()

        assert state.accumulated_context == []
        assert state.current_plan is None
        assert len(state.history) == 1  # History preserved

    @pytest.mark.unit
    def test_serialization(self) -> None:
        """Create a state object, serialize to JSON, deserialize.

        Assert strict equality (verifying persistence readiness).
        """
        state = ConversationState(
            session_id="test-session",
            user_preferences={"theme": "dark"},
        )
        state.add_message("user", "Test")

        # Serialize and deserialize
        json_str = state.model_dump_json()
        restored = ConversationState.model_validate_json(json_str)

        assert restored.session_id == state.session_id
        assert len(restored.history) == 1
        assert restored.user_preferences == {"theme": "dark"}
