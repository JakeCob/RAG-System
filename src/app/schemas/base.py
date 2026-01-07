"""Base schemas and shared models for inter-agent communication.

Reference: docs/02_AGENT_SPECS.md Section 2 & 4
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentMetadata(BaseModel):
    """Metadata attached to agent operations."""

    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model_version: str


class AgentFailure(BaseModel):
    """Standardized error object for agent failures.

    Reference: docs/02_AGENT_SPECS.md Section 4
    """

    agent_id: str
    error_code: str
    message: str
    recoverable: bool = False
    details: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Standard Error Codes (from AGENT_SPECS.md)
class ErrorCodes:
    """Standard error codes for agent failures."""

    # Guardrails
    GUARDRAIL_INJECTION = "ERR_GUARDRAIL_INJECTION"
    GUARDRAIL_UNSAFE = "ERR_GUARDRAIL_UNSAFE"

    # Connector
    CONNECTOR_AUTH = "ERR_CONNECTOR_AUTH"
    CONNECTOR_NOT_FOUND = "ERR_CONNECTOR_NOT_FOUND"
    CONNECTOR_RATE_LIMIT = "ERR_CONNECTOR_RATE_LIMIT"
    CONNECTOR_NETWORK = "ERR_CONNECTOR_NETWORK"

    # Parser
    PARSER_ENCRYPTED = "ERR_PARSER_ENCRYPTED"
    PARSER_UNSUPPORTED = "ERR_PARSER_UNSUPPORTED"

    # Memory
    MEMORY_NO_RESULTS = "ERR_MEMORY_NO_RESULTS"

    # Tailor
    TAILOR_HALLUCINATION = "ERR_TAILOR_HALLUCINATION"

    # General
    TIMEOUT = "ERR_TIMEOUT"


# Type aliases for common literals
SourceType = Literal["gdrive", "web", "local"]
IngestionSource = Literal["gdrive", "local", "web_scrape"]  # Per AGENT_SPECS.md
FileType = Literal["pdf", "html", "docx", "pptx", "txt", "md"]
LayoutType = Literal["text", "table", "image", "header"]
Persona = Literal["Technical", "Executive", "General"]
CheckType = Literal["input_validation", "output_safety"]
RiskCategory = Literal["injection", "pii", "hate_speech", "malicious_code", "none"]
PlanStatus = Literal["pending", "in_progress", "completed", "failed"]
MessageRole = Literal["user", "assistant", "system"]
