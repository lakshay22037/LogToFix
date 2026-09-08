import pytest
from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_current_user
from app.db import SessionLocal
from app.main import app
from app.models import LogSource, Project
from tests.test_persistence import requires_postgres

client = TestClient(app)

TEST_USER = CurrentUser(id="test-user-projects", email="test@example.com")


@pytest.fixture(autouse=True)
def authenticated():
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def created_project():
    response = client.post("/projects", json={"name": "My App"})
    assert response.status_code == 201
    project_id = response.json()["id"]

    yield project_id

    session = SessionLocal()
    session.query(LogSource).filter(LogSource.project_id == project_id).delete()
    session.query(Project).filter(Project.id == project_id).delete()
    session.commit()
    session.close()


@requires_postgres
def test_create_and_get_project(created_project):
    response = client.get(f"/projects/{created_project}")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "My App"
    assert body["source_count"] == 0


@requires_postgres
def test_list_projects_only_returns_own_projects(created_project):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id="someone-else", email="other@example.com")
    try:
        response = client.get("/projects")
        assert response.status_code == 200
        ids = [item["id"] for item in response.json()["items"]]
        assert created_project not in ids
    finally:
        app.dependency_overrides[get_current_user] = lambda: TEST_USER

    response = client.get("/projects")
    ids = [item["id"] for item in response.json()["items"]]
    assert created_project in ids


@requires_postgres
def test_get_project_404_for_someone_elses_project(created_project):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id="someone-else", email="other@example.com")
    try:
        response = client.get(f"/projects/{created_project}")
        assert response.status_code == 404
    finally:
        app.dependency_overrides[get_current_user] = lambda: TEST_USER


@requires_postgres
def test_create_file_source_is_active(created_project):
    response = client.post(
        f"/projects/{created_project}/sources",
        json={"name": "Prod logs", "source_type": "file", "config": {"path": "/var/log/app.log"}},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "active"
    assert body["source_type"] == "file"


@requires_postgres
def test_create_cloudwatch_source_is_coming_soon(created_project):
    response = client.post(
        f"/projects/{created_project}/sources",
        json={
            "name": "AWS prod",
            "source_type": "cloudwatch",
            "config": {"region": "us-east-1", "log_group": "/my-app/prod"},
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "coming_soon"


@requires_postgres
def test_list_sources_reflects_created_sources(created_project):
    client.post(f"/projects/{created_project}/sources", json={"name": "A", "source_type": "file", "config": {}})
    client.post(
        f"/projects/{created_project}/sources", json={"name": "B", "source_type": "azure_monitor", "config": {}}
    )

    response = client.get(f"/projects/{created_project}/sources")
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["items"]}
    assert names == {"A", "B"}


@requires_postgres
def test_project_source_count_reflects_created_sources(created_project):
    client.post(f"/projects/{created_project}/sources", json={"name": "A", "source_type": "file", "config": {}})

    response = client.get(f"/projects/{created_project}")
    assert response.json()["source_count"] == 1


@requires_postgres
def test_projects_endpoint_requires_auth():
    app.dependency_overrides.pop(get_current_user, None)
    try:
        assert client.get("/projects").status_code == 401
        assert client.post("/projects", json={"name": "x"}).status_code == 401
    finally:
        app.dependency_overrides[get_current_user] = lambda: TEST_USER
