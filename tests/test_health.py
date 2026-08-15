from fastapi.testclient import TestClient

from app.main import app


def test_health_check_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unversioned_health_path_is_not_exposed() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 404


def test_versioned_api_documentation_is_exposed() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/docs")

    assert response.status_code == 200
