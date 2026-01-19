"""FastAPI application exposing the ROMA RAG system."""

from __future__ import annotations

import json
import logging
import uuid
from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

from fastapi import (
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.agents import ROMAOrchestrator
from app.config import get_settings
from app.exceptions import AgentFailureError
from app.ingestion import IngestionService
from ingestion.dolphin import DolphinParser
from app.memory import MemoryAgent
from app.schemas import (
    AgentFailure,
    ErrorCodes,
    HealthStatus,
    IngestResponse,
    MemoryStatus,
    QueryRequest,
    StreamEvent,
    TailorOutput,
)


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


logger = logging.getLogger(__name__)

settings = get_settings()

_UPLOAD_FILE_PARAM = File(...)


@lru_cache


def _get_memory_agent() -> MemoryAgent:


    """Lazily initialize the vector store to avoid heavy imports at startup."""


    # Use the /data volume mount for persistent storage


    return MemoryAgent(db_path="/data/lancedb")











@lru_cache


def _get_ingestion_service() -> IngestionService:


    """Provide a cached ingestion service backed by the memory agent."""


    parser = DolphinParser(enable_ocr=settings.ingest_ocr_enabled)


    return IngestionService(memory_agent=_get_memory_agent(), parser=parser)











@lru_cache


def _get_orchestrator() -> ROMAOrchestrator:


    """Provide a cached orchestrator wired to the shared memory agent."""


    return ROMAOrchestrator(


        stream_chunk_pause_ms=settings.stream_chunk_pause_ms,


        memory_agent=_get_memory_agent(),


    )











app = FastAPI(


    title=settings.app_name,


    version="0.1.0",


    description="Multi-Source Agentic RAG System API",


)


app.add_middleware(


    CORSMiddleware,


    allow_origins=["*"],


    allow_credentials=True,


    allow_methods=["*"],


    allow_headers=["*"],


)











@app.get("/health", response_model=HealthStatus)


async def health() -> HealthStatus:


    """Return the readiness of dependent services."""








    return HealthStatus(db="connected", agents="ready")








@app.get("/inspect-database")


async def inspect_database(


    memory_agent: MemoryAgent = Depends(_get_memory_agent),


) -> dict[str, Any]:


    """


    Connects to the LanceDB database and returns the schema and a sample of


    the data from the 'documents' table.


    """


    table_name = "documents"  # As defined in lancedb_store.py


    try:


        table = memory_agent.store.db.open_table(table_name)


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





    # Remove the bulky 'embedding' for a clean response


    for record in sample_data:


        if "embedding" in record:


            del record["embedding"]





    return {


        "status": "success",


        "table_name": table_name,


        "schema": schema_str,


        "sample_records_count": len(sample_data),


        "sample_records": sample_data,


    }








@app.get("/memory/status", response_model=MemoryStatus)


async def memory_status() -> MemoryStatus:


    """Return summary stats for indexed documents."""

    memory = _get_memory_agent()
    return MemoryStatus(chunk_count=await memory.count_documents())


@app.post("/query", response_model=TailorOutput)
async def query_endpoint(payload: QueryRequest) -> TailorOutput | StreamingResponse:
    """Synchronous or streaming query execution."""
    orchestrator = _get_orchestrator()

    if payload.stream:
        stream = orchestrator.stream_query(payload)
        return StreamingResponse(
            content=_stream_sse(stream),
            media_type="text/event-stream",
        )

    try:
        result = await orchestrator.run_query(payload)
    except AgentFailureError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=jsonable_encoder(exc.failure),
        ) from exc

    return result.final_response


async def _authorize_ingest(authorization: str | None = Header(default=None)) -> None:
    """FastAPI dependency wrapping the auth validation."""

    _require_ingest_token(authorization)


def _require_ingest_token(authorization: str | None) -> None:
    """Validate Bearer token for ingestion requests."""

    if not settings.ingest_auth_enabled:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized("Missing Bearer token.")

    token = authorization.split(" ", maxsplit=1)[1]
    if token != settings.ingest_auth_token:
        raise _unauthorized("Invalid Bearer token.")


def _unauthorized(message: str) -> HTTPException:
    """Return a standardized HTTPException for auth failures."""

    failure = _agent_failure(
        agent_id="api.ingest",
        error_code=ErrorCodes.CONNECTOR_AUTH,
        message=message,
    )
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=failure,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _agent_failure(*, agent_id: str, error_code: str, message: str) -> dict[str, Any]:
    """Helper to serialize AgentFailure payloads."""

    failure = AgentFailure(agent_id=agent_id, error_code=error_code, message=message)
    return cast(dict[str, Any], jsonable_encoder(failure))


async def _stream_sse(
    events: AsyncGenerator[StreamEvent, None],
) -> AsyncGenerator[str, None]:
    """Convert StreamEvent objects into SSE formatted strings."""

    async for event in events:
        data = event.data
        serialized = (
            data if isinstance(data, str) else json.dumps(jsonable_encoder(data))
        )
        yield f"event: {event.event}\ndata: {serialized}\n\n"


async def _noop_ingest_job(filename: str, size_bytes: int) -> None:
    """Placeholder background ingestion task."""

    logger.debug("Ingested %s (%d bytes)", filename, size_bytes)


@app.post(
    "/ingest",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestResponse,
)
async def ingest_document(
    file: UploadFile = _UPLOAD_FILE_PARAM,
    _: None = Depends(_authorize_ingest),
) -> IngestResponse:
    """Accept a file for asynchronous ingestion."""
    ingestion_service = _get_ingestion_service()

    payload = await file.read()
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_agent_failure(
                agent_id="api.ingest",
                error_code=ErrorCodes.PARSER_UNSUPPORTED,
                message="Uploaded file is empty.",
            ),
        )

    task_id = str(uuid.uuid4())
    filename = file.filename or "upload.bin"
    try:
        await ingestion_service.ingest_document(
            content=payload,
            filename=filename,
            source_id=f"upload::{task_id}",
            source_type="local",
            extra_metadata={
                "content_type": file.content_type or "application/octet-stream"
            },
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_agent_failure(
                agent_id="api.ingest",
                error_code=ErrorCodes.PARSER_UNSUPPORTED,
                message=str(exc),
            ),
        ) from exc
    except AgentFailureError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=jsonable_encoder(exc.failure),
        ) from exc

    logger.info("Ingested %s via task %s", filename, task_id)
    return IngestResponse(task_id=task_id, filename=filename, status="queued")
