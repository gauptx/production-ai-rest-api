from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import router as api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Close the lazily-created queue connection during application shutdown."""
    yield
    queue = getattr(app.state, "arq_redis", None)
    if queue is not None:
        await queue.aclose()


app = FastAPI(
    title="Production AI REST API",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    redoc_url="/api/v1/redoc",
    lifespan=lifespan,
)
app.include_router(api_v1_router, prefix="/api/v1")
