from fastapi import FastAPI

from app.api.v1.router import router as api_v1_router

app = FastAPI(
    title="Production AI REST API",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    redoc_url="/api/v1/redoc",
)
app.include_router(api_v1_router, prefix="/api/v1")
