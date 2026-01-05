import os
import hashlib
from typing import Any
from src.app.schemas.connector import ConnectorOutput

class ConnectorAgent:
    """
    Connector Agent responsible for fetching and validating files.
    """

    def process_file(self, file_path: str, source_type: str = "local") -> ConnectorOutput:
        """
        Processes a local file and returns a ConnectorOutput.
        
        Args:
            file_path: Absolute path to the file.
            source_type: Type of source (local, etc.)
            
        Returns:
            ConnectorOutput: The processed file metadata.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        file_size = os.path.getsize(file_path)
        checksum = self._calculate_checksum(file_path)
        
        return ConnectorOutput(
            file_path=os.path.abspath(file_path),
            file_size_bytes=file_size,
            checksum=checksum,
            source_metadata={
                "source_type": source_type,
                "original_name": os.path.basename(file_path)
            }
        )
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculates MD5 checksum of a file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
