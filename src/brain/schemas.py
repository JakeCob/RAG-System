from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ContextNode(BaseModel):
    id: str
    text: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Citation(BaseModel):
    source_id: str
    text: str

class Answer(BaseModel):
    content: str
    citations: List[Citation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
