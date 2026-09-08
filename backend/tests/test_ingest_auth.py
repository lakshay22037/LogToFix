from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_current_user
from app.db import SessionLocal
from app.main import app
from app.models import LogSource, Project
from tests.test_persistence import requires_postgres

client = TestClient(app)

TEST_USER = CurrentUser(id="ingest-auth-test-user", email="test@example.com")


@pytest.fixture(autouse=True)
def authenticated():
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def project_and_source_with_key():
    response = client.post("/projects", json={"name": "Ingest Auth Test Project"})
    project_id = response.json()["id"]
    response = client.post(
        f"/projects/{project_id}/sources",
        json={"name": "Test Source", "source_type": "file", "config": {}},
    )
    body = response.json()

    yield body["id"], body["api_key"]

    session = SessionLocal()
    session.query(LogSource).filter(LogSource.project_id == project_id).delete()
    session.query(Project).filter(Project.id == project_id).delete()
    session.commit()
    session.close()


def _event_payload(source_id):
    return {
        "timestamp": datetime.now().isoformat(),
        "level": "ERROR",
        "service": "test",
        "message": "test",
        "source_type": "file",
        "raw": "raw",
        "source_id": source_id,
    }


@requires_postgres
def test_create_source_returns_plaintext_key_once(project_and_source_with_key):
    _, api_key = project_and_source_with_key
    assert api_key.startswith("src_")


@requires_postgres
def test_ingest_rejects_missing_api_key(project_and_source_with_key):
    source_id, _ = project_and_source_with_key
    response = client.post("/logs/ingest", json=_event_payload(source_id))
    assert response.status_code == 401


@requires_postgres
def test_ingest_rejects_wrong_api_key(project_and_source_with_key):
    source_id, _ = project_and_source_with_key
    response = client.post(
        "/logs/ingest", json=_event_payload(source_id), headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401


@requires_postgres
def test_ingest_accepts_correct_api_key(project_and_source_with_key):
    source_id, api_key = project_and_source_with_key
    response = client.post(
        "/logs/ingest", json=_event_payload(source_id), headers={"X-API-Key": api_key}
    )
    assert response.status_code == 202


@requires_postgres
def test_ingest_rejects_missing_source_id():
    payload = _event_payload(None)
    del payload["source_id"]
    response = client.post("/logs/ingest", json=payload, headers={"X-API-Key": "some-key"})
    assert response.status_code == 401
