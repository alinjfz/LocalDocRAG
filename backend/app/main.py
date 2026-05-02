"""
DocMind FastAPI application entry point.

Startup:
  - Initialises PostgreSQL tables via SQLAlchemy (respects EMBEDDING_DIMENSION)
  - Attaches all routers under /api prefix

Security:
  - CORS restricted to ALLOWED_ORIGINS from settings
  - slowapi rate limiting (per-IP, configured in nginx too for defence-in-depth)
  - Global exception handler returns consistent JSON error shape
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.database import init_db
from app.routers import auth, documents, evaluation, query

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Rate limiter (defence-in-depth — nginx also rate-limits externally) ───────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
# Init DB on startup, clean up on shutdown
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "DocMind starting — provider=%s embedding_dim=%d",
        settings.LLM_PROVIDER,
        settings.EMBEDDING_DIMENSION,
    )
    await init_db()
    logger.info("Database initialised — DocMind ready")
    yield
    logger.info("DocMind shutting down")


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="DocMind API",
    version="1.0.0",
    description=(
        "RAG-powered document intelligence system. "
        "Upload PDFs, ask questions, get grounded answers with page citations."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(evaluation.router)


# ── Root health check ─────────────────────────────────────────────────────────
@app.get("/", tags=["health"], summary="Health check")
async def root() -> dict:
    return {
        "status": "ok",
        "version": "1.0.0",
        "provider": settings.LLM_PROVIDER,
        "embedding_dimension": settings.EMBEDDING_DIMENSION,
    }


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred.", "status_code": 500},
    )
