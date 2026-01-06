"""Pydantic schemas for inter-agent communication.

Contains all shared types defined in docs/02_AGENT_SPECS.md:
- AgentMetadata, AgentFailure, ErrorCodes
- GuardrailsInput/Output
- ConnectorInput/Output
- ParserInput/Output, ParsedChunk
- MemoryQuery/Output, RetrievedContext
- TailorInput/Output, SourceCitation
- OrchestratorInput/Output, ConversationState
"""

from app.schemas.api import HealthStatus, IngestResponse, QueryRequest, StreamEvent
from app.schemas.base import AgentFailure, AgentMetadata, ErrorCodes
from app.schemas.connector import ConnectorInput, ConnectorOutput
from app.schemas.guardrails import GuardrailsInput, GuardrailsOutput
from app.schemas.memory import MemoryOutput, MemoryQuery, RetrievedContext
from app.schemas.orchestrator import (
    ConversationMessage,
    ConversationState,
    OrchestratorInput,
    OrchestratorOutput,
    PlanStep,
)
from app.schemas.parser import ParsedChunk, ParserInput, ParserOutput
from app.schemas.tailor import SourceCitation, TailorInput, TailorOutput


__all__ = [
    # Base
    "AgentMetadata",
    "AgentFailure",
    "ErrorCodes",
    # API
    "HealthStatus",
    "QueryRequest",
    "StreamEvent",
    "IngestResponse",
    # Guardrails
    "GuardrailsInput",
    "GuardrailsOutput",
    # Connector
    "ConnectorInput",
    "ConnectorOutput",
    # Parser
    "ParserInput",
    "ParsedChunk",
    "ParserOutput",
    # Memory
    "MemoryQuery",
    "RetrievedContext",
    "MemoryOutput",
    # Tailor
    "TailorInput",
    "TailorOutput",
    "SourceCitation",
    # Orchestrator
    "PlanStep",
    "OrchestratorInput",
    "OrchestratorOutput",
    "ConversationMessage",
    "ConversationState",
]
