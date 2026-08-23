"""Redis-backed fixed-window limits for authenticated operations."""

from arq.connections import ArqRedis
from fastapi import HTTPException, status

from app.core.config import SUMMARY_RATE_LIMIT, SUMMARY_RATE_LIMIT_WINDOW_SECONDS


async def enforce_summary_rate_limit(queue: ArqRedis, user_id: str) -> None:
    """Reject summary submissions that exceed a user's current time window."""
    key = f"rate-limit:summary:{user_id}"
    try:
        count = await queue.incr(key)
        if count == 1:
            await queue.expire(key, SUMMARY_RATE_LIMIT_WINDOW_SECONDS)
    except Exception as error:
        raise HTTPException(status_code=503, detail="summary queue unavailable") from error

    if count > SUMMARY_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="summary rate limit exceeded",
            headers={"Retry-After": str(SUMMARY_RATE_LIMIT_WINDOW_SECONDS)},
        )
