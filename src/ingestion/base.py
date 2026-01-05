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
        pass

    def chunk(self, text: str, limit: int = 1000) -> List[str]:
        """
        Splits text into smaller chunks based on a character limit.
        
        Args:
            text: The text to split.
            limit: Maximum characters per chunk.
            
        Returns:
            List[str]: A list of text chunks.
        """
        pass
