from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.crypto import CryptoNotConfigured, encrypt_secret
from app.db import get_session
from app.models import LogSource, Project, ProjectMember, generate_source_key, hash_source_key
from app.schemas.project import (
    ACTIVE_SOURCE_TYPES,
    LogSourceCreate,
    LogSourceCreated,
    LogSourceListResponse,
    LogSourceOut,
    ProjectCreate,
    ProjectListResponse,
    ProjectMemberInvite,
    ProjectMemberListResponse,
    ProjectMemberOut,
    ProjectOut,
    ProjectSettingsUpdate,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def get_owned_project(project_id: UUID, session: Session, current_user: CurrentUser) -> Project:
    """A project is visible to its owner or to anyone invited via
    ProjectMember whose email matched this user's on a prior sign-in (see
    accept_pending_memberships below) — see DECISIONS.md: "Team access"."""
    project = session.query(Project).filter(Project.id == project_id).first()
    is_owner = project is not None and project.owner_id == current_user.id
    is_member = (
        project is not None
        and not is_owner
        and session.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id)
        .first()
        is not None
    )
    if project is None or not (is_owner or is_member):
        # Same 404 whether the project doesn't exist or the user has no
        # access — don't leak which projects exist to users who can't see them.
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _accept_pending_memberships(session: Session, current_user: CurrentUser) -> None:
    """Supabase's user directory isn't queryable from our backend, so an
    invite (stored by email only) can't be resolved to a user id until
    that email actually signs in — this runs on every authenticated
    request to opportunistically claim any invites matching the caller."""
    pending = (
        session.query(ProjectMember)
        .filter(ProjectMember.email == current_user.email, ProjectMember.user_id.is_(None))
        .all()
    )
    if not pending:
        return
    for member in pending:
        member.user_id = current_user.id
    session.commit()


def _project_out(project: Project, source_count: int) -> ProjectOut:
    return ProjectOut(
        id=project.id,
        name=project.name,
        created_at=project.created_at,
        source_count=source_count,
        webhook_url=project.webhook_url,
        github_repo=project.github_repo,
        github_connected=bool(project.github_token_encrypted),
    )


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
    return _project_out(project, source_count=0)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    _accept_pending_memberships(session, current_user)

    member_project_ids = session.query(ProjectMember.project_id).filter(ProjectMember.user_id == current_user.id)
    rows = (
        session.query(Project, func.count(LogSource.id))
        .outerjoin(LogSource, LogSource.project_id == Project.id)
        .filter((Project.owner_id == current_user.id) | (Project.id.in_(member_project_ids)))
        .group_by(Project.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    items = [_project_out(project, count) for project, count in rows]
    return ProjectListResponse(items=items)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: UUID,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    project = get_owned_project(project_id, session, current_user)
    source_count = session.query(LogSource).filter(LogSource.project_id == project.id).count()
    return _project_out(project, source_count)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project_settings(
    project_id: UUID,
    body: ProjectSettingsUpdate,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    project = session.query(Project).filter(Project.id == project_id).first()
    if project is None or project.owner_id != current_user.id:
        # Settings (webhook, GitHub token) are owner-only — a shared
        # member can see and triage issues but not repoint alerts or
        # rotate the repo's PR credentials.
        raise HTTPException(status_code=404, detail="Project not found")

    if body.webhook_url is not None:
        project.webhook_url = body.webhook_url or None
    if body.github_repo is not None:
        project.github_repo = body.github_repo or None
    if body.github_token:
        try:
            project.github_token_encrypted = encrypt_secret(body.github_token)
        except CryptoNotConfigured as exc:
            raise HTTPException(status_code=500, detail="GitHub integration is not configured on this server") from exc

    session.commit()
    session.refresh(project)
    source_count = session.query(LogSource).filter(LogSource.project_id == project.id).count()
    return _project_out(project, source_count)


@router.post("/{project_id}/sources", response_model=LogSourceCreated, status_code=201)
def create_log_source(
    project_id: UUID,
    body: LogSourceCreate,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    project = get_owned_project(project_id, session, current_user)
    status = "active" if body.source_type in ACTIVE_SOURCE_TYPES else "coming_soon"
    plaintext_key = generate_source_key()
    source = LogSource(
        project_id=project.id,
        name=body.name,
        source_type=body.source_type,
        config=body.config,
        status=status,
        api_key_hash=hash_source_key(plaintext_key),
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    return LogSourceCreated(
        id=source.id,
        name=source.name,
        source_type=source.source_type,
        config=source.config,
        status=source.status,
        created_at=source.created_at,
        api_key=plaintext_key,
    )


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
    return LogSourceListResponse(items=[LogSourceOut.model_validate(s) for s in sources])


@router.post("/{project_id}/members", response_model=ProjectMemberOut, status_code=201)
def invite_member(
    project_id: UUID,
    body: ProjectMemberInvite,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    project = session.query(Project).filter(Project.id == project_id).first()
    if project is None or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = (
        session.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.email == body.email)
        .first()
    )
    if existing:
        return existing

    member = ProjectMember(project_id=project_id, email=body.email)
    session.add(member)
    session.commit()
    session.refresh(member)
    return member


@router.get("/{project_id}/members", response_model=ProjectMemberListResponse)
def list_members(
    project_id: UUID,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    get_owned_project(project_id, session, current_user)
    members = session.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    return ProjectMemberListResponse(items=members)


@router.delete("/{project_id}/members/{member_id}", status_code=204)
def remove_member(
    project_id: UUID,
    member_id: UUID,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    project = session.query(Project).filter(Project.id == project_id).first()
    if project is None or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    member = (
        session.query(ProjectMember)
        .filter(ProjectMember.id == member_id, ProjectMember.project_id == project_id)
        .first()
    )
    if member is not None:
        session.delete(member)
        session.commit()
