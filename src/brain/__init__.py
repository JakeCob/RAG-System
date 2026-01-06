"""Brain (RAG Engine) module for retrieval-augmented generation.

Provides the core RAG functionality:
- RAGEngine: Main engine for retrieve + generate pipeline
- Schemas: ContextNode, Answer, Citation, QueryResult, etc.
- Error handling: RAGFailure, RAGErrorCodes
"""

from brain.engine import RAGEngine
from brain.schemas import (
    Answer,
    Citation,
    ContextNode,
    GenerateConfig,
    Persona,
    QueryConfig,
    QueryResult,
    RAGErrorCodes,
    RAGFailure,
    RetrieveConfig,
)


__all__ = [
    # Engine
    "RAGEngine",
    # Core schemas
    "ContextNode",
    "Citation",
    "Answer",
    "QueryResult",
    # Config schemas
    "RetrieveConfig",
    "GenerateConfig",
    "QueryConfig",
    "Persona",
    # Error handling
    "RAGFailure",
    "RAGErrorCodes",
]
