"""FastAPI application exposing the ROMA RAG system."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncGenerator

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
from app.config import APISettings, get_settings
from app.exceptions import AgentFailureError
from app.ingestion import IngestionService
from app.memory import MemoryAgent
from app.schemas import (
    AgentFailure,
    ErrorCodes,
    HealthStatus,
    IngestResponse,
    QueryRequest,
    StreamEvent,
    TailorOutput,
)


logger = logging.getLogger(__name__)

settings = get_settings()
memory_agent = MemoryAgent(db_path=".lancedb")
ingestion_service = IngestionService(memory_agent=memory_agent)
orchestrator = ROMAOrchestrator(
    stream_chunk_pause_ms=settings.stream_chunk_pause_ms,
    memory_agent=memory_agent,
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


@app.post("/query", response_model=TailorOutput)
async def query_endpoint(payload: QueryRequest) -> TailorOutput | StreamingResponse:
    """Synchronous or streaming query execution."""

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


def _agent_failure(*, agent_id: str, error_code: str, message: str) -> dict:
    """Helper to serialize AgentFailure payloads."""

    failure = AgentFailure(agent_id=agent_id, error_code=error_code, message=message)
    return jsonable_encoder(failure)


async def _stream_sse(
    events: AsyncGenerator[StreamEvent, None],
) -> AsyncGenerator[str, None]:
    """Convert StreamEvent objects into SSE formatted strings."""

    async for event in events:
        data = event.data
        serialized = data if isinstance(data, str) else json.dumps(data)
        yield f"event: {event.event}\ndata: {serialized}\n\n"


async def _noop_ingest_job(filename: str, size_bytes: int) -> None:
    """Placeholder background ingestion task."""

    logger.debug("Ingested %s (%d bytes)", filename, size_bytes)


@app.post("/ingest", status_code=status.HTTP_202_ACCEPTED, response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    _: None = Depends(_authorize_ingest),
) -> IngestResponse:
    """Accept a file for asynchronous ingestion."""

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
    try:
        await ingestion_service.ingest_document(
            content=payload,
            filename=file.filename,
            source_id=f"upload::{task_id}",
            source_type="local",
            extra_metadata={"content_type": file.content_type or "application/octet-stream"},
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

    logger.info("Ingested %s via task %s", file.filename, task_id)
    return IngestResponse(task_id=task_id, filename=file.filename, status="queued")
