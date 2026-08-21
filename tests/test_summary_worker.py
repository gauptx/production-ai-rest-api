import asyncio

import pytest
from arq import Retry
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base
from app.models import SummaryJob, User
from app.workers.summary import process_summary_job


class FakeSummaryProvider:
    def __init__(self, result: str | None = "Short summary.") -> None:
        self.result = result

    async def summarize(self, text: str) -> str:
        if self.result is None:
            raise RuntimeError("provider unavailable")
        return self.result


def test_worker_marks_queued_job_completed_with_provider_result() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        user = User(email="worker@example.com", password_hash="not-used-in-this-test")
        session.add(user)
        session.flush()
        job = SummaryJob(user_id=user.id, input_text="Text to process.")
        session.add(job)
        session.commit()

        assert asyncio.run(process_summary_job(session, job.id, FakeSummaryProvider())) is True

        processed_job = session.get(SummaryJob, job.id)
        assert processed_job is not None
        assert processed_job.status == "completed"
        assert processed_job.result == "Short summary."
        assert processed_job.failure_code is None
        assert asyncio.run(process_summary_job(session, job.id, FakeSummaryProvider())) is False
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_worker_marks_queued_job_failed_when_provider_errors() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        user = User(email="failure@example.com", password_hash="not-used-in-this-test")
        session.add(user)
        session.flush()
        job = SummaryJob(user_id=user.id, input_text="Text to process.")
        session.add(job)
        session.commit()

        assert asyncio.run(process_summary_job(session, job.id, FakeSummaryProvider(None))) is True

        processed_job = session.get(SummaryJob, job.id)
        assert processed_job is not None
        assert processed_job.status == "failed"
        assert processed_job.failure_code == "provider_error"
        assert processed_job.result is None
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_worker_retries_transient_provider_failure_then_records_terminal_failure() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        user = User(email="retry@example.com", password_hash="not-used-in-this-test")
        session.add(user)
        session.flush()
        job = SummaryJob(user_id=user.id, input_text="Text to process.")
        session.add(job)
        session.commit()

        with pytest.raises(Retry) as retry:
            asyncio.run(
                process_summary_job(
                    session,
                    job.id,
                    FakeSummaryProviderError(ConnectionError("offline")),
                )
            )
        assert retry.value.defer_score == 2_000
        assert session.get(SummaryJob, job.id).status == "processing"

        assert (
            asyncio.run(
                process_summary_job(
                    session,
                    job.id,
                    FakeSummaryProviderError(ConnectionError("offline")),
                    attempt=3,
                )
            )
            is True
        )
        processed_job = session.get(SummaryJob, job.id)
        assert processed_job is not None
        assert processed_job.status == "failed"
        assert processed_job.failure_code == "provider_unavailable"
    finally:
        session.close()
        Base.metadata.drop_all(engine)


class FakeSummaryProviderError:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def summarize(self, text: str) -> str:
        raise self.error
