from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.models import FixSuggestionRecord, Issue, LogSource
from app.routers.projects import get_owned_project
from app.schemas.analytics import DailyCount, ProjectAnalytics, ServiceCount

router = APIRouter(prefix="/projects/{project_id}/analytics", tags=["analytics"])


@router.get("", response_model=ProjectAnalytics)
def get_analytics(
    project_id: UUID,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    get_owned_project(project_id, session, current_user)

    base = session.query(Issue).join(LogSource, LogSource.id == Issue.log_source_id).filter(
        LogSource.project_id == project_id
    )

    total_issues = base.count()
    open_issues = base.filter(Issue.status.in_(["open", "acknowledged"])).count()
    resolved_issues = base.filter(Issue.status == "resolved").count()
    total_occurrences = base.with_entities(func.coalesce(func.sum(Issue.occurrence_count), 0)).scalar()

    avg_confidence = (
        session.query(func.avg(FixSuggestionRecord.confidence))
        .join(Issue, Issue.id == FixSuggestionRecord.issue_id)
        .join(LogSource, LogSource.id == Issue.log_source_id)
        .filter(LogSource.project_id == project_id)
        .scalar()
    )

    daily_rows = (
        base.with_entities(func.date(Issue.first_seen).label("day"), func.count(Issue.id))
        .group_by("day")
        .order_by("day")
        .all()
    )
    issues_per_day = [DailyCount(date=str(day), count=count) for day, count in daily_rows]

    service_rows = (
        base.with_entities(Issue.service, func.count(Issue.id))
        .group_by(Issue.service)
        .order_by(func.count(Issue.id).desc())
        .limit(10)
        .all()
    )
    top_services = [ServiceCount(service=service, count=count) for service, count in service_rows]

    avg_resolution_seconds = (
        base.filter(Issue.status == "resolved", Issue.resolved_at.isnot(None))
        .with_entities(func.avg(func.extract("epoch", Issue.resolved_at - Issue.first_seen)))
        .scalar()
    )
    avg_resolution_hours = (avg_resolution_seconds / 3600) if avg_resolution_seconds is not None else None

    return ProjectAnalytics(
        total_issues=total_issues,
        open_issues=open_issues,
        resolved_issues=resolved_issues,
        total_occurrences=int(total_occurrences or 0),
        avg_confidence=float(avg_confidence) if avg_confidence is not None else None,
        issues_per_day=issues_per_day,
        top_services=top_services,
        avg_resolution_hours=avg_resolution_hours,
    )
