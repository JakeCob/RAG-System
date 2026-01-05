from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import lancedb
import os
import random
from typing import List, Optional
from loaders import load_from_urls, load_from_gdrive

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
    text: str
    vector: List[float]
    metadata: dict

class URLIngestRequest(BaseModel):
    urls: List[str]
    browser: str = "chrome"

class GDriveIngestRequest(BaseModel):
    folder_id: Optional[str] = None
    document_ids: Optional[List[str]] = None

def _mock_embed(text: str, dim: int = 128) -> List[float]:
    """Generates a random vector for prototyping purposes."""
    return [random.random() for _ in range(dim)]

def _store_in_lancedb(text: str, metadata: dict):
    if not db:
        print("DB not active, skipping storage")
        return False
    
    vector = _mock_embed(text)
    table_name = "knowledge_base"
    try:
        tbl = db.open_table(table_name)
        tbl.add([{"vector": vector, "text": text, "metadata": metadata}])
    except:
        data = [{"vector": vector, "text": text, "metadata": metadata}]
        db.create_table(table_name, data=data)
    return True

@app.get("/")
async def root():
    return {
        "message": "ROMA-Dolphin RAG System Online",
        "modules": {
            "parsing": ["Dolphin (Simulated)", "Selenium", "Google Drive"],
            "orchestration": "ROMA Agents",
            "storage": ["LanceDB", "PostgreSQL"]
        }
    }

@app.post("/ingest")
async def ingest_chunk(chunk: DocumentChunk):
    """
    Simulates a ROMA Ingestion Node receiving parsed data from Dolphin.
    """
    if not db:
        raise HTTPException(status_code=500, detail="Vector DB not active")
    
    # Simple table management for demo
    table_name = "knowledge_base"
    try:
        tbl = db.open_table(table_name)
    except:
        # Create table if not exists - Schema typically inferred in LanceDB
        # For strict typing, pyarrow schema is better, but this is vibe coding.
        data = [{"vector": chunk.vector, "text": chunk.text, "metadata": chunk.metadata}]
        tbl = db.create_table(table_name, data=data)
        return {"status": "created_table", "id": 1}

    tbl.add([{"vector": chunk.vector, "text": chunk.text, "metadata": chunk.metadata}])
    return {"status": "ingested", "chunks_added": 1}

@app.post("/ingest/url")
async def ingest_url(request: URLIngestRequest):
    """
    Ingests content from provided URLs using Selenium.
    """
    docs = load_from_urls(request.urls, request.browser)
    count = 0
    for doc in docs:
        if _store_in_lancedb(doc['text'], doc['metadata']):
            count += 1
            
    return {"status": "processed", "urls_processed": len(request.urls), "chunks_stored": count}

@app.post("/ingest/gdrive")
async def ingest_gdrive(request: GDriveIngestRequest):
    """
    Ingests content from Google Drive (Folder ID or Document IDs).
    Requires credentials.json and token.json to be present in backend/.
    """
    docs = load_from_gdrive(folder_id=request.folder_id, document_ids=request.document_ids)
    count = 0
    for doc in docs:
        if _store_in_lancedb(doc['text'], doc['metadata']):
            count += 1
            
    return {"status": "processed", "chunks_stored": count}
