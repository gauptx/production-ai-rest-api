import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.logging import log_event
from app.core.queue import get_queue

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Report that the API process is available.

    This endpoint only proves the API process is accepting requests.
    """
    return {"status": "ok"}


@router.get("/readiness")
async def readiness_check(request: Request) -> JSONResponse:
    """Verify that the database and job queue are reachable."""
    dependencies: dict[str, str] = {}
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        dependencies["database"] = "ok"
    except Exception:
        dependencies["database"] = "unavailable"

    try:
        queue = await get_queue(request)
        await queue.ping()
        dependencies["queue"] = "ok"
    except Exception:
        dependencies["queue"] = "unavailable"

    ready = all(value == "ok" for value in dependencies.values())
    response_status = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE
    log_event(
        logger,
        "readiness_checked",
        dependencies=dependencies,
        request_id=getattr(request.state, "request_id", None),
        ready=ready,
    )
    return JSONResponse(
        status_code=response_status,
        content={"status": "ok" if ready else "unavailable"},
    )
