import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_current_user
from app.db import SessionLocal
from app.main import app
from app.models import FixSuggestionRecord, Issue, LogSource, Project, hash_source_key
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
    source = LogSource(
        project_id=project.id,
        name="Test Source",
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
    session.query(LogSource).filter(LogSource.id == source_id).delete()
    session.query(Project).filter(Project.id == project_id).delete()
    session.commit()
    session.close()


@pytest.fixture
def seeded_issue(project_and_source):
    _, source_id = project_and_source
    session = SessionLocal()
    now = datetime.now()
    issue = Issue(
        log_source_id=source_id,
        fingerprint="abc123",
        title="test error for API test",
        level="ERROR",
        service="orders",
        occurrence_count=3,
        first_seen=now,
        last_seen=now,
        commit_hash="abc123def456",
        commit_author="Test Author",
        commit_summary="Test commit",
        file_path="app.py",
        line_number=42,
    )
    session.add(issue)
    session.flush()
    fix = FixSuggestionRecord(
        issue_id=issue.id,
        explanation="test explanation",
        diff="- old\n+ new",
        confidence=0.75,
    )
    session.add(fix)
    session.commit()
    issue_id = issue.id
    session.close()

    yield issue_id

    session = SessionLocal()
    session.query(FixSuggestionRecord).filter(FixSuggestionRecord.issue_id == issue_id).delete()
    session.query(Issue).filter(Issue.id == issue_id).delete()
    session.commit()
    session.close()


@requires_postgres
def test_list_issues_includes_seeded_issue(project_and_source, seeded_issue):
    project_id, _ = project_and_source
    response = client.get(f"/projects/{project_id}/issues", params={"limit": 100})
    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 100
    ids = [item["id"] for item in body["items"]]
    assert str(seeded_issue) in ids

    matching = next(item for item in body["items"] if item["id"] == str(seeded_issue))
    assert matching["confidence"] == 0.75
    assert matching["commit_hash"] == "abc123def456"
    assert matching["occurrence_count"] == 3


@requires_postgres
def test_list_issues_respects_limit_bounds(project_and_source):
    project_id, _ = project_and_source
    response = client.get(f"/projects/{project_id}/issues", params={"limit": 9999})
    assert response.status_code == 200
    assert response.json()["limit"] == 100  # clamped


@requires_postgres
def test_get_issue_detail(project_and_source, seeded_issue):
    project_id, _ = project_and_source
    response = client.get(f"/projects/{project_id}/issues/{seeded_issue}")
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "test error for API test"
    assert body["fix_suggestion"]["confidence"] == 0.75
    assert body["fix_suggestion"]["diff"] == "- old\n+ new"


@requires_postgres
def test_get_issue_detail_404_for_unknown_id(project_and_source):
    project_id, _ = project_and_source
    response = client.get(f"/projects/{project_id}/issues/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@requires_postgres
def test_list_issues_404_for_project_owned_by_someone_else(project_and_source):
    project_id, _ = project_and_source
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id="a-different-user", email="other@example.com")
    try:
        response = client.get(f"/projects/{project_id}/issues")
        assert response.status_code == 404
    finally:
        app.dependency_overrides[get_current_user] = lambda: TEST_USER


@requires_postgres
def test_ingest_response_has_cors_header_for_allowed_origin():
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


@requires_postgres
def test_issues_endpoint_requires_auth(project_and_source):
    project_id, _ = project_and_source
    app.dependency_overrides.pop(get_current_user, None)
    try:
        assert client.get(f"/projects/{project_id}/issues").status_code == 401
    finally:
        app.dependency_overrides[get_current_user] = lambda: TEST_USER


@requires_postgres
def test_patch_issue_status(project_and_source, seeded_issue):
    project_id, _ = project_and_source
    response = client.patch(f"/projects/{project_id}/issues/{seeded_issue}", json={"status": "acknowledged"})
    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"


@requires_postgres
def test_resolving_issue_adds_verified_suggestion_to_fix_corpus(project_and_source, seeded_issue):
    from app.models import FixExample

    project_id, _ = project_and_source
    response = client.patch(f"/projects/{project_id}/issues/{seeded_issue}", json={"status": "resolved"})
    assert response.status_code == 200

    session = SessionLocal()
    try:
        example = (
            session.query(FixExample)
            .filter(FixExample.source == "resolved_issue", FixExample.error_description == "test error for API test")
            .first()
        )
        assert example is not None
        assert example.fix_diff == "- old\n+ new"
    finally:
        if example is not None:
            session.delete(example)
            session.commit()
        session.close()
