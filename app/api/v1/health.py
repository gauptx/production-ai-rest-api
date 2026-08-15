from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Report that the API process is available.

    Dependency readiness checks belong to a later milestone.
    """
    return {"status": "ok"}
