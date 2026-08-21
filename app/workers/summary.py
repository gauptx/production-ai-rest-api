"""Background processing for persisted summary jobs."""

from typing import Any, Protocol

from arq import Retry
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import SummaryJob
from app.services.summarizer import OllamaSummaryProvider, is_transient_ollama_error

MAX_PROVIDER_ATTEMPTS = 3
RETRY_DELAYS_SECONDS = (2, 5)


class SummaryProvider(Protocol):
    """The summarization capability required by the worker."""

    async def summarize(self, text: str) -> str: ...


async def process_summary(ctx: dict[str, Any], job_id: str) -> None:
    """Claim a queued job and process it with the configured provider."""
    with SessionLocal() as db:
        await process_summary_job(
            db,
            job_id,
            OllamaSummaryProvider(),
            attempt=ctx["job_try"],
        )


async def process_summary_job(
    db: Session,
    job_id: str,
    provider: SummaryProvider,
    *,
    attempt: int = 1,
) -> bool:
    """Process one queued job, returning whether this worker claimed it.

    Transient provider failures are retried with a bounded delay. All other
    failures are recorded safely rather than leaving jobs in ``processing``.
    """
    job = db.get(SummaryJob, job_id)
    if job is None or job.status not in {"queued", "processing"}:
        return False

    if job.status == "queued":
        job.status = "processing"
        db.commit()

    try:
        job.result = await provider.summarize(job.input_text)
    except Exception as error:
        if is_transient_ollama_error(error) and attempt < MAX_PROVIDER_ATTEMPTS:
            db.commit()
            raise Retry(defer=RETRY_DELAYS_SECONDS[attempt - 1]) from error
        job.status = "failed"
        job.failure_code = (
            "provider_unavailable" if is_transient_ollama_error(error) else "provider_error"
        )
    else:
        job.status = "completed"
        job.failure_code = None
    db.commit()
    return True
