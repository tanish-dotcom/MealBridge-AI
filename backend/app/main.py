"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.api.deps import get_db
from app.api.router import api_router
from app.core.config import settings
from app.core.database import check_database_connection
from app.core.rate_limit import limiter
from app.core.security import decode_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment == "development":
        from app.models import Base  # noqa: F401

    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    lifespan=lifespan,
)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def attach_actor(request: Request, call_next):
    """Best-effort: expose the JWT subject to handlers (for audit logging)."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        claims = decode_token(auth[7:], expected_type="access")
        if claims:
            request.state.current_user_id = claims["sub"]
    return await call_next(request)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Too many requests. Please slow down."})


# Local dev static media (S3 in production serves these instead).
_local_media = Path(settings.local_storage_dir)
_local_media.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_local_media)), name="media")

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    return {"app": settings.app_name, "docs": "/docs", "health": "/api/v1/health"}
