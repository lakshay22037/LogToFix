from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_current_user
from app.db import SessionLocal
from app.main import app
from app.models import FixSuggestionRecord, LogEventRecord, LogSource, Project
from tests.test_persistence import requires_postgres

client = TestClient(app)

TEST_USER = CurrentUser(id="test-user", email="test@example.com")


@pytest.fixture(autouse=True)
def authenticated():
    """Overrides auth for every test in this file — these tests exercise
    endpoint behavior, not the auth layer itself (see test_auth.py)."""
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def project_and_source():
    session = SessionLocal()
    project = Project(owner_id=TEST_USER.id, name="Test Project")
    session.add(project)
    session.flush()
    source = LogSource(project_id=project.id, name="Test Source", source_type="file", status="active")
    session.add(source)
    session.commit()
    project_id, source_id = project.id, source.id
    session.close()

    yield project_id, source_id

    session = SessionLocal()
    session.query(LogSource).filter(LogSource.id == source_id).delete()
    session.query(Project).filter(Project.id == project_id).delete()
    session.commit()
    session.close()


@pytest.fixture
def seeded_error(project_and_source):
    _, source_id = project_and_source
    session = SessionLocal()
    log_event = LogEventRecord(
        log_source_id=source_id,
        timestamp=datetime.now(),
        level="ERROR",
        service="orders",
        message="test error for API test",
        stack_trace="Traceback...\nValueError: test",
        source_type="file",
        raw="raw",
        commit_hash="abc123def456",
        commit_author="Test Author",
        commit_summary="Test commit",
        file_path="app.py",
        line_number=42,
    )
    session.add(log_event)
    session.flush()
    fix = FixSuggestionRecord(
        log_event_id=log_event.id,
        explanation="test explanation",
        diff="- old\n+ new",
        confidence=0.75,
    )
    session.add(fix)
    session.commit()
    event_id = log_event.id
    session.close()

    yield event_id

    session = SessionLocal()
    session.query(FixSuggestionRecord).filter(FixSuggestionRecord.log_event_id == event_id).delete()
    session.query(LogEventRecord).filter(LogEventRecord.id == event_id).delete()
    session.commit()
    session.close()


@requires_postgres
def test_list_errors_includes_seeded_error(project_and_source, seeded_error):
    project_id, _ = project_and_source
    response = client.get(f"/projects/{project_id}/errors", params={"limit": 100})
    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 100
    ids = [item["id"] for item in body["items"]]
    assert str(seeded_error) in ids

    matching = next(item for item in body["items"] if item["id"] == str(seeded_error))
    assert matching["confidence"] == 0.75
    assert matching["commit_hash"] == "abc123def456"


@requires_postgres
def test_list_errors_respects_limit_bounds(project_and_source):
    project_id, _ = project_and_source
    response = client.get(f"/projects/{project_id}/errors", params={"limit": 9999})
    assert response.status_code == 200
    assert response.json()["limit"] == 100  # clamped


@requires_postgres
def test_get_error_detail(project_and_source, seeded_error):
    project_id, _ = project_and_source
    response = client.get(f"/projects/{project_id}/errors/{seeded_error}")
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "test error for API test"
    assert body["fix_suggestion"]["confidence"] == 0.75
    assert body["fix_suggestion"]["diff"] == "- old\n+ new"


@requires_postgres
def test_get_error_detail_404_for_unknown_id(project_and_source):
    project_id, _ = project_and_source
    response = client.get(f"/projects/{project_id}/errors/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@requires_postgres
def test_list_errors_404_for_project_owned_by_someone_else(project_and_source):
    project_id, _ = project_and_source
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id="a-different-user", email="other@example.com")
    try:
        response = client.get(f"/projects/{project_id}/errors")
        assert response.status_code == 404
    finally:
        app.dependency_overrides[get_current_user] = lambda: TEST_USER


@requires_postgres
def test_ingest_response_has_cors_header_for_allowed_origin():
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


@requires_postgres
def test_errors_endpoint_requires_auth(project_and_source):
    project_id, _ = project_and_source
    app.dependency_overrides.pop(get_current_user, None)
    try:
        assert client.get(f"/projects/{project_id}/errors").status_code == 401
    finally:
        app.dependency_overrides[get_current_user] = lambda: TEST_USER
