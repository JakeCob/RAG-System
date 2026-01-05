"""Connector Agent schemas.

Reference: docs/02_AGENT_SPECS.md Section 2.1
"""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.base import SourceType


class ConnectorInput(BaseModel):
    """Input for the Connector Agent."""

    source_type: SourceType
    source_identifier: str = Field(..., description="URL, File Path, or GDrive File ID")
    credentials_id: str | None = None
    recursive: bool = False


class ConnectorOutput(BaseModel):
    """Output from the Connector Agent."""

    file_path: str = Field(
        ..., description="Local absolute path to the downloaded file"
    )
    file_size_bytes: int
    source_metadata: dict[str, Any] = Field(
        ..., description="Original metadata (e.g., GDrive author, URL headers)"
    )
    checksum: str
