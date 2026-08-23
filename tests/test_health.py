import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_health_check_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_health_check_preserves_supplied_request_id() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/health", headers={"X-Request-ID": "request-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-123"


def test_unversioned_health_path_is_not_exposed() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 404


def test_versioned_api_documentation_is_exposed() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/docs")

    assert response.status_code == 200


class FakeReadySession:
    def __enter__(self) -> "FakeReadySession":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: object) -> None:
        return None


class FakeReadyQueue:
    async def ping(self) -> bool:
        return True


@pytest.mark.parametrize(
    ("database_available", "queue_available", "expected_status"),
    [(True, True, 200), (False, True, 503), (True, False, 503)],
)
def test_readiness_checks_database_and_queue(
    monkeypatch: pytest.MonkeyPatch,
    database_available: bool,
    queue_available: bool,
    expected_status: int,
) -> None:
    from app.api.v1 import health

    class UnavailableSession(FakeReadySession):
        def __enter__(self) -> "UnavailableSession":
            raise ConnectionError("database offline")

    async def get_ready_queue(_: object) -> FakeReadyQueue:
        if not queue_available:
            raise ConnectionError("queue offline")
        return FakeReadyQueue()

    monkeypatch.setattr(
        health, "SessionLocal", FakeReadySession if database_available else UnavailableSession
    )
    monkeypatch.setattr(health, "get_queue", get_ready_queue)
    client = TestClient(app)

    response = client.get("/api/v1/readiness")

    assert response.status_code == expected_status
    assert response.json() == {"status": "ok" if expected_status == 200 else "unavailable"}
