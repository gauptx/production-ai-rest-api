"""Summary-job creation endpoints.

Background processing is introduced in Milestone 2. This endpoint establishes
the authenticated persistence boundary by recording a queued job.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.db import get_db
from app.models import SummaryJob, User

router = APIRouter(prefix="/summaries", tags=["summaries"])


class CreateSummaryRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)


class SummaryJobResponse(BaseModel):
    id: str
    status: str
    input_text: str
    result: str | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime


@router.post("", response_model=SummaryJobResponse, status_code=status.HTTP_201_CREATED)
def create_summary(
    request: CreateSummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SummaryJob:
    """Persist a queued job for the authenticated user.

    No queue work is enqueued until the asynchronous processing milestone.
    """
    job = SummaryJob(user_id=current_user.id, input_text=request.text, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}", response_model=SummaryJobResponse)
def get_summary(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SummaryJob:
    """Return an authenticated user's own persisted summary job."""
    job = db.get(SummaryJob, job_id)
    if job is None or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="summary job not found")
    return job
