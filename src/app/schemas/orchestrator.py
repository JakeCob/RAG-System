"""ROMA Orchestrator schemas.

Reference: docs/02_AGENT_SPECS.md Section 2.5 & 3
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import MessageRole, PlanStatus
from app.schemas.memory import RetrievedContext
from app.schemas.tailor import TailorOutput


class PlanStep(BaseModel):
    """A single step in the orchestrator's execution plan."""

    step_id: int
    description: str
    tool_call: str
    status: PlanStatus


class OrchestratorInput(BaseModel):
    """Input for the Orchestrator."""

    user_message: str
    session_id: str
    user_id: str


class OrchestratorOutput(BaseModel):
    """Output from the Orchestrator."""

    final_response: TailorOutput
    execution_plan: list[PlanStep]
    processing_time_total_ms: float


# --- State Management (Section 3) ---


class ConversationMessage(BaseModel):
    """A single message in the conversation history."""

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationState(BaseModel):
    """State object maintained by the Orchestrator.

    Reference: docs/02_AGENT_SPECS.md Section 3
    """

    session_id: str
    history: list[ConversationMessage] = Field(default_factory=list)

    # Short-term Memory / Working Context for the current turn
    current_plan: list[PlanStep] | None = None
    accumulated_context: list[RetrievedContext] = Field(default_factory=list)

    # Metadata for the session
    user_preferences: dict[str, object] = Field(default_factory=dict)

    def add_message(self, role: MessageRole, content: str) -> None:
        """Add a message to the conversation history."""
        self.history.append(
            ConversationMessage(role=role, content=content, timestamp=datetime.utcnow())
        )

    def clear_context(self) -> None:
        """Clear working context while preserving history."""
        self.accumulated_context = []
        self.current_plan = None
