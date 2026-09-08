from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.models import FixSuggestionRecord, LogEventRecord, LogSource
from app.routers.projects import get_owned_project
from app.schemas.error import ErrorDetail, ErrorListItem, ErrorListResponse

router = APIRouter(prefix="/projects/{project_id}/errors", tags=["errors"])


@router.get("", response_model=ErrorListResponse)
def list_errors(
    project_id: UUID,
    limit: int = 20,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    get_owned_project(project_id, session, current_user)  # 404s if not owned
    limit = max(1, min(limit, 100))  # never an unbounded result set
    offset = max(0, offset)

    query = (
        session.query(LogEventRecord, FixSuggestionRecord.confidence)
        .join(LogSource, LogSource.id == LogEventRecord.log_source_id)
        .outerjoin(FixSuggestionRecord, FixSuggestionRecord.log_event_id == LogEventRecord.id)
        .filter(LogSource.project_id == project_id)
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


@router.get("/{error_id}", response_model=ErrorDetail)
def get_error(
    project_id: UUID,
    error_id: UUID,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    get_owned_project(project_id, session, current_user)  # 404s if not owned

    log_event: Optional[LogEventRecord] = (
        session.query(LogEventRecord)
        .join(LogSource, LogSource.id == LogEventRecord.log_source_id)
        .filter(LogEventRecord.id == error_id, LogSource.project_id == project_id)
        .first()
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
