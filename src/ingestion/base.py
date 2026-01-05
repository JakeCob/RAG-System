import uuid
from typing import List, Union, Dict, Any
from src.app.schemas.parser import ParsedChunk

class BaseParser:
    """Base class for all ingestion parsers."""

    def parse(self, content: Union[str, bytes], metadata: Dict[str, Any]) -> List[ParsedChunk]:
        """
        Parses raw content into structured chunks.
        
        Args:
            content: Raw file content (str or bytes).
            metadata: Metadata associated with the content (e.g., URL, title).
            
        Returns:
            List[ParsedChunk]: A list of structured chunks.
        """
        if isinstance(content, bytes):
            # Simple decode for bytes, assuming utf-8 for this skeleton
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
        else:
            text = content
            
        if not text:
            raise ValueError("Content cannot be empty.")
            
        chunks_text = self.chunk(text)
        parsed_chunks = []
        
        for i, chunk_text in enumerate(chunks_text):
            parsed_chunks.append(
                ParsedChunk(
                    chunk_id=str(uuid.uuid4()),
                    content=chunk_text,
                    chunk_index=i,
                    layout_type="text"
                )
            )
        return parsed_chunks

    def chunk(self, text: str, limit: int = 1000) -> List[str]:
        """
        Splits text into smaller chunks based on a character limit.
        
        Args:
            text: The text to split.
            limit: Maximum characters per chunk.
            
        Returns:
            List[str]: A list of text chunks.
        """
        return [text[i:i+limit] for i in range(0, len(text), limit)]