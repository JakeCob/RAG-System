from typing import List, Any
from src.brain.schemas import ContextNode, Answer, Citation

class RAGEngine:
    def __init__(self, vector_store: Any, llm_client: Any):
        self.vector_store = vector_store
        self.llm_client = llm_client

    async def retrieve(self, query: str) -> List[ContextNode]:
        results = await self.vector_store.search(query)
        nodes = []
        for res in results:
            nodes.append(ContextNode(
                id=res.get("id"),
                text=res.get("content", ""),
                score=res.get("score", 0.0),
                metadata=res.get("metadata", {})
            ))
        return nodes

    async def generate_answer(self, query: str, context: List[ContextNode]) -> Answer:
        context_str = "\n".join([f"- {node.text}" for node in context])
        prompt = f"Context:\n{context_str}\n\nQuery: {query}"
        
        response_text = await self.llm_client.complete(prompt)
        
        citations = []
        for node in context:
            # Create citation from context metadata
            citations.append(Citation(
                source_id=str(node.metadata.get("url", "unknown")),
                text=node.text[:50] + "..." if len(node.text) > 50 else node.text
            ))

        return Answer(
            content=response_text,
            citations=citations,
            metadata={"model": "rag-model-v1"}
        )