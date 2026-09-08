import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import app.env  # noqa: F401 — loads .env as a side effect
from app.db import get_session
from app.logging_config import configure_logging, correlation_id_var
from app.models import FixSuggestionRecord, LogEventRecord
from app.rate_limit import enforce_rate_limit
from app.schemas.error import ErrorDetail, ErrorListItem, ErrorListResponse
from app.schemas.log_event import NormalizedLogEvent
from app.tasks import process_log_event

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # uvicorn installs its own log handlers during server startup, which
    # runs after this module is imported — calling configure_logging() at
    # import time gets silently overridden. This lifespan startup phase
    # runs after uvicorn's own logging setup, so this call is the one that
    # sticks.
    configure_logging()
    yield


app = FastAPI(title="Log-to-Fix", lifespan=lifespan)

# Scoped to the frontend's actual origin — never a wildcard (see
# DECISIONS.md's security review: CORS was deliberately deferred until a
# real frontend existed to scope this to).
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    token = correlation_id_var.set(correlation_id)
    try:
        response = await call_next(request)
    finally:
        correlation_id_var.reset(token)
    response.headers["X-Request-ID"] = correlation_id
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/logs/ingest", status_code=202, dependencies=[Depends(enforce_rate_limit)])
def ingest_log(event: NormalizedLogEvent):
    if event.correlation_id is None:
        event.correlation_id = correlation_id_var.get()
    logger.info("Ingested event: %s [%s] %s", event.level, event.service, event.message)
    process_log_event.delay(event.model_dump(mode="json"))
    return {"accepted": True}


@app.get("/errors", response_model=ErrorListResponse)
def list_errors(
    limit: int = 20,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    limit = max(1, min(limit, 100))  # never an unbounded result set
    offset = max(0, offset)

    query = (
        session.query(
            LogEventRecord,
            FixSuggestionRecord.confidence,
        )
        .outerjoin(FixSuggestionRecord, FixSuggestionRecord.log_event_id == LogEventRecord.id)
        .order_by(LogEventRecord.created_at.desc())
    )
    total = query.count()
    rows = query.offset(offset).limit(limit).all()

    items = [
        ErrorListItem(
            id=log_event.id,
            timestamp=log_event.timestamp,
            level=log_event.level,
            service=log_event.service,
            message=log_event.message,
            commit_hash=log_event.commit_hash,
            commit_summary=log_event.commit_summary,
            confidence=confidence,
        )
        for log_event, confidence in rows
    ]
    return ErrorListResponse(items=items, total=total, limit=limit, offset=offset)


@app.get("/errors/{error_id}", response_model=ErrorDetail)
def get_error(error_id: UUID, session: Session = Depends(get_session)):
    log_event: Optional[LogEventRecord] = (
        session.query(LogEventRecord).filter(LogEventRecord.id == error_id).first()
    )
    if log_event is None:
        raise HTTPException(status_code=404, detail="Error not found")

    fix_suggestion = (
        session.query(FixSuggestionRecord)
        .filter(FixSuggestionRecord.log_event_id == error_id)
        .order_by(FixSuggestionRecord.created_at.desc())
        .first()
    )

    return ErrorDetail(
        id=log_event.id,
        timestamp=log_event.timestamp,
        level=log_event.level,
        service=log_event.service,
        message=log_event.message,
        stack_trace=log_event.stack_trace,
        file_path=log_event.file_path,
        line_number=log_event.line_number,
        commit_hash=log_event.commit_hash,
        commit_author=log_event.commit_author,
        commit_summary=log_event.commit_summary,
        fix_suggestion=fix_suggestion,
    )
