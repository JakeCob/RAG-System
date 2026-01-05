from typing import List, Any
from src.brain.schemas import ContextNode, Answer

class RAGEngine:
    def __init__(self, vector_store: Any, llm_client: Any):
        self.vector_store = vector_store
        self.llm_client = llm_client

    async def retrieve(self, query: str) -> List[ContextNode]:
        raise NotImplementedError("Retrieve not implemented")

    async def generate_answer(self, query: str, context: List[ContextNode]) -> Answer:
        raise NotImplementedError("Generate answer not implemented")