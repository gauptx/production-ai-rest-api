import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.queue import get_queue
from app.main import app


class FakeQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    async def enqueue_job(self, function: str, *args: object, **kwargs: object) -> object:
        self.calls.append((function, args, kwargs))
        return object()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    database_url = os.getenv("TEST_DATABASE_URL", "sqlite://")
    engine_kwargs: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        engine_kwargs = {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    engine = create_engine(database_url, **engine_kwargs)
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    fake_queue = FakeQueue()

    async def override_get_queue() -> FakeQueue:
        return fake_queue

    app.dependency_overrides[get_queue] = override_get_queue
    with TestClient(app) as test_client:
        test_client.app.state.test_queue = fake_queue
        yield test_client
    app.dependency_overrides.clear()
    del app.state.test_queue
    Base.metadata.drop_all(engine)


def test_register_login_refresh_and_protected_route(client: TestClient) -> None:
    credentials = {"email": "person@example.com", "password": "correct-horse-battery"}

    registered = client.post("/api/v1/auth/register", json=credentials)
    assert registered.status_code == 201
    tokens = registered.json()
    assert tokens["token_type"] == "bearer"

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == credentials["email"]

    logged_in = client.post("/api/v1/auth/login", json=credentials)
    assert logged_in.status_code == 200

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != tokens["refresh_token"]

    replayed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replayed.status_code == 401


def test_invalid_login_and_unauthenticated_route_are_rejected(client: TestClient) -> None:
    credentials = {"email": "person@example.com", "password": "correct-horse-battery"}
    client.post("/api/v1/auth/register", json=credentials)

    response = client.post(
        "/api/v1/auth/login", json={"email": credentials["email"], "password": "wrong-password"}
    )
    assert response.status_code == 401

    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_authenticated_user_can_create_a_persisted_summary_job(client: TestClient) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "person@example.com", "password": "correct-horse-battery"},
    )
    access_token = registered.json()["access_token"]

    created = client.post(
        "/api/v1/summaries",
        json={"text": "A short document to summarize later."},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert created.status_code == 201
    assert created.json()["status"] == "queued"
    assert created.json()["id"]
    assert created.json()["created_at"]
    assert client.app.state.test_queue.calls == [
        ("process_summary", (created.json()["id"],), {"_job_id": created.json()["id"]})
    ]

    retrieved = client.get(
        f"/api/v1/summaries/{created.json()['id']}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert retrieved.status_code == 200
    assert retrieved.json()["input_text"] == "A short document to summarize later."


def test_user_cannot_read_another_users_summary_job(client: TestClient) -> None:
    first_user = client.post(
        "/api/v1/auth/register",
        json={"email": "first@example.com", "password": "correct-horse-battery"},
    ).json()
    second_user = client.post(
        "/api/v1/auth/register",
        json={"email": "second@example.com", "password": "correct-horse-battery"},
    ).json()
    created = client.post(
        "/api/v1/summaries",
        json={"text": "Private text."},
        headers={"Authorization": f"Bearer {first_user['access_token']}"},
    )

    response = client.get(
        f"/api/v1/summaries/{created.json()['id']}",
        headers={"Authorization": f"Bearer {second_user['access_token']}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "summary job not found"}


def test_summary_job_creation_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/summaries", json={"text": "Unauthenticated text."})

    assert response.status_code == 401
