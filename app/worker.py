"""ARQ worker configuration for asynchronous summary processing."""

from arq.connections import RedisSettings

from app.core.config import REDIS_URL
from app.workers.summary import MAX_PROVIDER_ATTEMPTS, process_summary


class WorkerSettings:
    """Configuration loaded by the ARQ worker process.

    Transient provider failures are retried up to a bounded attempt limit.
    """

    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    functions = [process_summary]
    max_tries = MAX_PROVIDER_ATTEMPTS
