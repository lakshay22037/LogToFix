from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

import uuid

import app.tasks as tasks
from app.db import SessionLocal, engine
from app.models import FixSuggestionRecord, Issue, LogEventRecord, LogSource, Project, hash_source_key
from app.schemas.log_event import LogLevel, NormalizedLogEvent, SourceType


def _postgres_reachable() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


requires_postgres = pytest.mark.skipif(
    not _postgres_reachable(), reason="Postgres not reachable at DATABASE_URL"
)


@pytest.fixture
def project_and_source():
    session = SessionLocal()
    project = Project(owner_id="persist-test-user", name="Persistence Test Project")
    session.add(project)
    session.flush()
    source = LogSource(
        project_id=project.id,
        name="Persistence Test Source",
        source_type="file",
        status="active",
        api_key_hash=hash_source_key(f"test-key-{uuid.uuid4()}"),
    )
    session.add(source)
    session.commit()
    project_id, source_id = project.id, source.id
    session.close()

    yield project_id, source_id

    session = SessionLocal()
    issue_ids = [i.id for i in session.query(Issue).filter(Issue.log_source_id == source_id).all()]
    session.query(FixSuggestionRecord).filter(FixSuggestionRecord.issue_id.in_(issue_ids)).delete(
        synchronize_session=False
    )
    session.query(LogEventRecord).filter(LogEventRecord.log_source_id == source_id).delete()
    session.query(Issue).filter(Issue.log_source_id == source_id).delete()
    session.query(LogSource).filter(LogSource.id == source_id).delete()
    session.query(Project).filter(Project.id == project_id).delete()
    session.commit()
    session.close()


def _event(source_id, message="a test error for the persistence test", stack_trace="Traceback...\nValueError: test"):
    return NormalizedLogEvent(
        timestamp=datetime.now(),
        level=LogLevel.ERROR,
        service="test-service",
        message=message,
        stack_trace=stack_trace,
        source_type=SourceType.FILE,
        raw="raw log line for test",
        source_id=source_id,
    )


@requires_postgres
def test_process_creates_issue_and_fix_suggestion(project_and_source, monkeypatch):
    _, source_id = project_and_source
    correlation = {
        "commit": "deadbeef" * 5,
        "author": "Test Author",
        "summary": "Test commit summary",
        "file": "app.py",
        "line": 1,
        "repo_root": "/tmp",
    }
    monkeypatch.setattr(tasks, "correlate_error_to_commit", lambda stack_trace: correlation)
    monkeypatch.setattr(tasks, "read_code_context", lambda *a, **k: "1: pass")

    tasks._process(_event(source_id))

    session = SessionLocal()
    try:
        issue = session.query(Issue).filter(Issue.log_source_id == source_id).first()
        assert issue is not None
        assert issue.occurrence_count == 1
        assert issue.commit_hash == correlation["commit"]

        log_event_row = session.query(LogEventRecord).filter(LogEventRecord.issue_id == issue.id).first()
        assert log_event_row is not None

        fix_row = session.query(FixSuggestionRecord).filter(FixSuggestionRecord.issue_id == issue.id).first()
        assert fix_row is not None  # fake LLM provider always returns a suggestion
    finally:
        session.close()


@requires_postgres
def test_repeated_occurrence_dedupes_into_same_issue(project_and_source, monkeypatch):
    _, source_id = project_and_source
    correlation = {
        "commit": "cafebabe" * 5,
        "author": "Test Author",
        "summary": "Test commit summary",
        "file": "app.py",
        "line": 2,
        "repo_root": "/tmp",
    }
    monkeypatch.setattr(tasks, "correlate_error_to_commit", lambda stack_trace: correlation)
    monkeypatch.setattr(tasks, "read_code_context", lambda *a, **k: "1: pass")

    tasks._process(_event(source_id, message="repeated bug"))
    tasks._process(_event(source_id, message="repeated bug"))
    tasks._process(_event(source_id, message="repeated bug"))

    session = SessionLocal()
    try:
        issues = session.query(Issue).filter(Issue.log_source_id == source_id).all()
        assert len(issues) == 1
        assert issues[0].occurrence_count == 3

        log_events = session.query(LogEventRecord).filter(LogEventRecord.issue_id == issues[0].id).all()
        assert len(log_events) == 3

        fix_suggestions = session.query(FixSuggestionRecord).filter(FixSuggestionRecord.issue_id == issues[0].id).all()
        # Only one LLM call for the first occurrence — not re-diagnosed per duplicate.
        assert len(fix_suggestions) == 1
    finally:
        session.close()


@requires_postgres
def test_uncorrelated_event_still_creates_issue_without_suggestion(project_and_source, monkeypatch):
    _, source_id = project_and_source
    monkeypatch.setattr(tasks, "correlate_error_to_commit", lambda stack_trace: None)

    tasks._process(_event(source_id, message="uncorrelated error"))

    session = SessionLocal()
    try:
        issue = session.query(Issue).filter(Issue.log_source_id == source_id).first()
        assert issue is not None
        assert issue.commit_hash is None

        fix_row = session.query(FixSuggestionRecord).filter(FixSuggestionRecord.issue_id == issue.id).first()
        assert fix_row is None
    finally:
        session.close()
