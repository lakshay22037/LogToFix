from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_current_user
from app.db import SessionLocal
from app.main import app
from app.models import FixSuggestionRecord, LogEventRecord
from tests.test_persistence import requires_postgres

client = TestClient(app)


@pytest.fixture(autouse=True)
def authenticated():
    """Overrides auth for every test in this file — these tests exercise
    /errors endpoint behavior, not the auth layer itself (see
    test_auth.py for that), so a fixed fake user keeps them focused."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id="test-user", email="test@example.com")
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def seeded_error():
    session = SessionLocal()
    log_event = LogEventRecord(
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
def test_list_errors_includes_seeded_error(seeded_error):
    response = client.get("/errors", params={"limit": 100})
    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 100
    ids = [item["id"] for item in body["items"]]
    assert str(seeded_error) in ids

    matching = next(item for item in body["items"] if item["id"] == str(seeded_error))
    assert matching["confidence"] == 0.75
    assert matching["commit_hash"] == "abc123def456"


@requires_postgres
def test_list_errors_respects_limit_bounds():
    response = client.get("/errors", params={"limit": 9999})
    assert response.status_code == 200
    assert response.json()["limit"] == 100  # clamped


@requires_postgres
def test_get_error_detail(seeded_error):
    response = client.get(f"/errors/{seeded_error}")
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "test error for API test"
    assert body["fix_suggestion"]["confidence"] == 0.75
    assert body["fix_suggestion"]["diff"] == "- old\n+ new"


@requires_postgres
def test_get_error_detail_404_for_unknown_id():
    response = client.get("/errors/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@requires_postgres
def test_ingest_response_has_cors_header_for_allowed_origin():
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


@requires_postgres
def test_errors_endpoints_require_auth():
    # Remove the override just for these two assertions, so the real
    # dependency (requiring a valid Authorization header) actually runs.
    app.dependency_overrides.pop(get_current_user, None)
    try:
        assert client.get("/errors").status_code == 401
        assert client.get("/errors/00000000-0000-0000-0000-000000000000").status_code == 401
    finally:
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(id="test-user", email="test@example.com")
