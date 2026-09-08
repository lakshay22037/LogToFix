import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from llm_core.embeddings import EmbeddingError, get_default_embedder
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.db import SessionLocal, get_session
from app.github_integration import GitHubIntegrationError, open_pull_request
from app.models import FixExample, FixSuggestionRecord, Issue, LogEventRecord, LogSource
from app.routers.projects import get_owned_project
from app.schemas.issue import (
    FixSuggestionOut,
    IssueDetail,
    IssueListItem,
    IssueListResponse,
    IssueStatusUpdate,
    OpenPrRequest,
    OpenPrResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/issues", tags=["issues"])


def _latest_suggestion(session: Session, issue_id: UUID) -> Optional[FixSuggestionRecord]:
    return (
        session.query(FixSuggestionRecord)
        .filter(FixSuggestionRecord.issue_id == issue_id)
        .order_by(FixSuggestionRecord.created_at.desc())
        .first()
    )


def _latest_stack_trace(session: Session, issue_id: UUID) -> Optional[str]:
    event = (
        session.query(LogEventRecord)
        .filter(LogEventRecord.issue_id == issue_id)
        .order_by(LogEventRecord.created_at.desc())
        .first()
    )
    return event.stack_trace if event else None


def _get_issue_or_404(project_id: UUID, issue_id: UUID, session: Session) -> Issue:
    issue = (
        session.query(Issue)
        .join(LogSource, LogSource.id == Issue.log_source_id)
        .filter(Issue.id == issue_id, LogSource.project_id == project_id)
        .first()
    )
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.get("", response_model=IssueListResponse)
def list_issues(
    project_id: UUID,
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    get_owned_project(project_id, session, current_user)  # 404s if not accessible
    limit = max(1, min(limit, 100))  # never an unbounded result set
    offset = max(0, offset)

    query = (
        session.query(Issue)
        .join(LogSource, LogSource.id == Issue.log_source_id)
        .filter(LogSource.project_id == project_id)
    )
    if status:
        query = query.filter(Issue.status == status)
    query = query.order_by(Issue.last_seen.desc())

    total = query.count()
    page = query.offset(offset).limit(limit).all()

    # One suggestion per issue at most, so fetching the latest per
    # issue_id in Python (rather than a correlated subquery) keeps this
    # simple and avoids SQLAlchemy auto-correlation pitfalls.
    latest_confidence = {}
    if page:
        issue_ids = [issue.id for issue in page]
        for suggestion in (
            session.query(FixSuggestionRecord)
            .filter(FixSuggestionRecord.issue_id.in_(issue_ids))
            .order_by(FixSuggestionRecord.created_at.desc())
            .all()
        ):
            latest_confidence.setdefault(suggestion.issue_id, suggestion.confidence)

    items = [
        IssueListItem(
            id=issue.id,
            title=issue.title,
            level=issue.level,
            service=issue.service,
            status=issue.status,
            occurrence_count=issue.occurrence_count,
            first_seen=issue.first_seen,
            last_seen=issue.last_seen,
            commit_hash=issue.commit_hash,
            commit_summary=issue.commit_summary,
            confidence=latest_confidence.get(issue.id),
        )
        for issue in page
    ]
    return IssueListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{issue_id}", response_model=IssueDetail)
def get_issue(
    project_id: UUID,
    issue_id: UUID,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    get_owned_project(project_id, session, current_user)
    issue = _get_issue_or_404(project_id, issue_id, session)
    suggestion = _latest_suggestion(session, issue_id)

    return IssueDetail(
        id=issue.id,
        title=issue.title,
        level=issue.level,
        service=issue.service,
        status=issue.status,
        occurrence_count=issue.occurrence_count,
        first_seen=issue.first_seen,
        last_seen=issue.last_seen,
        stack_trace=_latest_stack_trace(session, issue_id),
        file_path=issue.file_path,
        line_number=issue.line_number,
        commit_hash=issue.commit_hash,
        commit_author=issue.commit_author,
        commit_summary=issue.commit_summary,
        fix_suggestion=FixSuggestionOut.model_validate(suggestion) if suggestion else None,
    )


@router.patch("/{issue_id}", response_model=IssueDetail)
def update_issue_status(
    project_id: UUID,
    issue_id: UUID,
    body: IssueStatusUpdate,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    get_owned_project(project_id, session, current_user)
    issue = _get_issue_or_404(project_id, issue_id, session)

    issue.status = body.status
    # Issue.first_seen/last_seen come from the log source's own event
    # timestamps (its local wall clock — see FileTailAdapter), not this
    # server's UTC clock. resolved_at needs to be on the same clock to
    # produce a meaningful delta for the resolution-time analytics
    # (mixing local-source time against server UTC time would otherwise
    # yield a skewed or even negative duration whenever they're in
    # different zones).
    issue.resolved_at = datetime.now() if body.status == "resolved" else None

    suggestion = _latest_suggestion(session, issue_id)
    if body.status == "resolved" and suggestion is not None and not suggestion.added_to_knowledge_base:
        _add_to_fix_corpus(issue, suggestion)
        suggestion.added_to_knowledge_base = True

    session.commit()
    session.refresh(issue)

    return IssueDetail(
        id=issue.id,
        title=issue.title,
        level=issue.level,
        service=issue.service,
        status=issue.status,
        occurrence_count=issue.occurrence_count,
        first_seen=issue.first_seen,
        last_seen=issue.last_seen,
        stack_trace=_latest_stack_trace(session, issue_id),
        file_path=issue.file_path,
        line_number=issue.line_number,
        commit_hash=issue.commit_hash,
        commit_author=issue.commit_author,
        commit_summary=issue.commit_summary,
        fix_suggestion=FixSuggestionOut.model_validate(suggestion) if suggestion else None,
    )


def _add_to_fix_corpus(issue: Issue, suggestion: FixSuggestionRecord) -> None:
    """Feature: fix outcome feedback loop. A human marking an issue
    "resolved" is a real, verified confirmation that this suggestion
    actually worked — much stronger ground truth than an unvalidated LLM
    output, so it's worth growing the RAG corpus (see DECISIONS.md:
    "Data sourcing strategy") with it. Best-effort: embedding failures
    must not block the status change itself."""
    try:
        embedding = get_default_embedder().embed(issue.title)
    except EmbeddingError:
        logger.exception("Failed to embed resolved issue for fix_examples corpus; skipping")
        return

    session = SessionLocal()
    try:
        session.add(FixExample(
            error_description=issue.title,
            fix_diff=suggestion.diff,
            source="resolved_issue",
            embedding=embedding,
        ))
        session.commit()
    finally:
        session.close()


@router.post("/{issue_id}/open-pr", response_model=OpenPrResponse)
def open_pr(
    project_id: UUID,
    issue_id: UUID,
    body: OpenPrRequest,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    project = get_owned_project(project_id, session, current_user)
    issue = _get_issue_or_404(project_id, issue_id, session)
    suggestion = _latest_suggestion(session, issue_id)
    if suggestion is None:
        raise HTTPException(status_code=400, detail="No fix suggestion to open a PR for")

    try:
        pr_url = open_pull_request(project, issue, suggestion, base_branch=body.base_branch)
    except GitHubIntegrationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return OpenPrResponse(pr_url=pr_url)
