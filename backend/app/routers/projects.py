from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.db import get_session
from app.models import LogSource, Project
from app.schemas.project import (
    ACTIVE_SOURCE_TYPES,
    LogSourceCreate,
    LogSourceListResponse,
    LogSourceOut,
    ProjectCreate,
    ProjectListResponse,
    ProjectOut,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def get_owned_project(project_id: UUID, session: Session, current_user: CurrentUser) -> Project:
    project = session.query(Project).filter(Project.id == project_id).first()
    if project is None or project.owner_id != current_user.id:
        # Same 404 whether the project doesn't exist or belongs to someone
        # else — don't leak which projects exist to users who don't own them.
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    body: ProjectCreate,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    project = Project(owner_id=current_user.id, name=body.name)
    session.add(project)
    session.commit()
    session.refresh(project)
    return ProjectOut(id=project.id, name=project.name, created_at=project.created_at, source_count=0)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    rows = (
        session.query(Project, func.count(LogSource.id))
        .outerjoin(LogSource, LogSource.project_id == Project.id)
        .filter(Project.owner_id == current_user.id)
        .group_by(Project.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    items = [
        ProjectOut(id=project.id, name=project.name, created_at=project.created_at, source_count=count)
        for project, count in rows
    ]
    return ProjectListResponse(items=items)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: UUID,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    project = get_owned_project(project_id, session, current_user)
    source_count = session.query(LogSource).filter(LogSource.project_id == project.id).count()
    return ProjectOut(id=project.id, name=project.name, created_at=project.created_at, source_count=source_count)


@router.post("/{project_id}/sources", response_model=LogSourceOut, status_code=201)
def create_log_source(
    project_id: UUID,
    body: LogSourceCreate,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    project = get_owned_project(project_id, session, current_user)
    status = "active" if body.source_type in ACTIVE_SOURCE_TYPES else "coming_soon"
    source = LogSource(
        project_id=project.id,
        name=body.name,
        source_type=body.source_type,
        config=body.config,
        status=status,
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


@router.get("/{project_id}/sources", response_model=LogSourceListResponse)
def list_log_sources(
    project_id: UUID,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    project = get_owned_project(project_id, session, current_user)
    sources = (
        session.query(LogSource)
        .filter(LogSource.project_id == project.id)
        .order_by(LogSource.created_at.desc())
        .all()
    )
    return LogSourceListResponse(items=sources)
