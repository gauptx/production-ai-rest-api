import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.router import router as api_v1_router
from app.core.logging import configure_structured_logging, log_event

configure_structured_logging()
logger = logging.getLogger(__name__)


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


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    """Attach a correlation ID and emit safe, structured request logs."""
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    log_event(
        logger,
        "request_completed",
        method=request.method,
        path=request.url.path,
        request_id=request_id,
        status_code=response.status_code,
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, error: Exception) -> JSONResponse:
    """Log unexpected failures internally without exposing implementation details."""
    request_id = getattr(request.state, "request_id", None)
    logger.exception("unhandled_request_error request_id=%s", request_id)
    return JSONResponse(
        status_code=500,
        content={"detail": "internal server error"},
        headers={"X-Request-ID": request_id} if request_id else {},
    )


app.include_router(api_v1_router, prefix="/api/v1")
