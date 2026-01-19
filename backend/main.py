"""FastAPI backend prototype for the RAG system.

This module provides minimal ingestion endpoints backed by LanceDB.
"""

import os
import random
from typing import Any

import lancedb
from fastapi import FastAPI, HTTPException
from .loaders import load_from_gdrive, load_from_urls
from pydantic import BaseModel


app = FastAPI(title="ROMA-Dolphin RAG System")

# Configuration
LANCEDB_URI = os.getenv("LANCEDB_URI", "/data/lancedb")

# Initialize LanceDB
# In a real ROMA setup, this would be wrapped in a specific 'StorageAgent'
try:
    os.makedirs(LANCEDB_URI, exist_ok=True)
    db = lancedb.connect(LANCEDB_URI)
except Exception as e:
    print(f"Warning: Could not connect to LanceDB at {LANCEDB_URI}: {e}")
    db = None


class DocumentChunk(BaseModel):
    """A single chunk payload for ingestion."""

    text: str
    vector: list[float]
    metadata: dict[str, Any]


class URLIngestRequest(BaseModel):
    """Request payload for URL ingestion."""

    urls: list[str]
    browser: str = "chrome"


class GDriveIngestRequest(BaseModel):
    """Request payload for Google Drive ingestion."""

    folder_id: str | None = None
    document_ids: list[str] | None = None


def _mock_embed(_text: str, dim: int = 128) -> list[float]:
    """Generates a random vector for prototyping purposes."""
    return [random.random() for _ in range(dim)]


def _store_in_lancedb(text: str, metadata: dict[str, Any]) -> bool:
    """Store a single text+metadata record in LanceDB.

    Args:
        text: Text content to store.
        metadata: Arbitrary metadata to associate with the record.

    Returns:
        True if stored successfully, otherwise False.
    """
    if not db:
        print("DB not active, skipping storage")
        return False

    vector = _mock_embed(text)
    table_name = "knowledge_base"
    try:
        tbl = db.open_table(table_name)
        tbl.add([{"vector": vector, "text": text, "metadata": metadata}])
    except Exception:
        data = [{"vector": vector, "text": text, "metadata": metadata}]
        db.create_table(table_name, data=data)
    return True


@app.get("/")
async def root() -> dict[str, Any]:
    """Return API health and module metadata."""
    return {
        "message": "ROMA-Dolphin RAG System Online",
        "modules": {
            "parsing": ["Dolphin (Simulated)", "Selenium", "Google Drive"],
            "orchestration": "ROMA Agents",
            "storage": ["LanceDB", "PostgreSQL"],
        },
    }


@app.post("/ingest")
async def ingest_chunk(chunk: DocumentChunk) -> dict[str, Any]:
    """Ingest a single pre-parsed chunk into LanceDB."""
    if not db:
        raise HTTPException(status_code=500, detail="Vector DB not active")

    # Simple table management for demo
    table_name = "knowledge_base"
    try:
        tbl = db.open_table(table_name)
    except Exception:
        # Create table if not exists - Schema typically inferred in LanceDB
        # For strict typing, pyarrow schema is better, but this is vibe coding.
        data = [
            {"vector": chunk.vector, "text": chunk.text, "metadata": chunk.metadata}
        ]
        tbl = db.create_table(table_name, data=data)
        return {"status": "created_table", "id": 1}

    tbl.add([{"vector": chunk.vector, "text": chunk.text, "metadata": chunk.metadata}])
    return {"status": "ingested", "chunks_added": 1}


@app.post("/ingest/url")
async def ingest_url(request: URLIngestRequest) -> dict[str, Any]:
    """Ingest URL content and store each fetched document into LanceDB."""
    docs = load_from_urls(request.urls, request.browser)
    count = 0
    for doc in docs:
        if _store_in_lancedb(doc["text"], doc["metadata"]):
            count += 1

    return {
        "status": "processed",
        "urls_processed": len(request.urls),
        "chunks_stored": count,
    }


@app.post("/ingest/gdrive")
async def ingest_gdrive(request: GDriveIngestRequest) -> dict[str, Any]:
    """Ingest Google Drive content and store each fetched document into LanceDB.

    Requires `credentials.json` and `token.json` in `backend/` by default.
    """
    docs = load_from_gdrive(
        folder_id=request.folder_id, document_ids=request.document_ids
    )
    count = 0
    for doc in docs:
        if _store_in_lancedb(doc["text"], doc["metadata"]):
            count += 1

    return {"status": "processed", "chunks_stored": count}


@app.get("/inspect-database")
async def inspect_database():
    """
    Connects to the LanceDB database and returns the schema and a sample of
    the data from the 'knowledge_base' table.
    """
    if not db:
        raise HTTPException(status_code=500, detail="Vector DB not active")

    table_name = "knowledge_base"
    try:
        table = db.open_table(table_name)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Table '{table_name}' not found. Has any data been ingested? Error: {e}",
        )

    # Get schema and convert to a readable string format
    schema_str = str(table.schema)

    # Get the first 5 records as a list of dictionaries
    try:
        sample_data = table.search().limit(5).to_list()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve data from table. It might be empty. Error: {e}",
        )


    # Remove the bulky 'vector' embedding for a clean response
    for record in sample_data:
        if "vector" in record:
            del record["vector"]

    return {
        "status": "success",
        "table_name": table_name,
        "schema": schema_str,
        "sample_records_count": len(sample_data),
        "sample_records": sample_data,
    }
