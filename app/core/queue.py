"""ARQ queue dependency shared by API endpoints."""

from typing import cast

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi import Request

from app.core.config import REDIS_URL


async def get_queue(request: Request) -> ArqRedis:
    """Return the application-scoped ARQ Redis connection pool."""
    queue = getattr(request.app.state, "arq_redis", None)
    if queue is None:
        queue = await create_pool(RedisSettings.from_dsn(REDIS_URL))
        request.app.state.arq_redis = queue
    return cast(ArqRedis, queue)
