"""
Step 231: FastAPI application – gateway for dashboard and health. Reuses existing services.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from amazon_research.logging_config import get_logger
from amazon_research.api_gateway.routers import health, workspaces, discovery, copilot

logger = get_logger("api_gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load env, init DB if possible, log. Shutdown: no-op."""
    from dotenv import load_dotenv
    load_dotenv()
    try:
        from amazon_research.db import init_db
        init_db()
    except Exception as e:
        logger.warning("api_gateway db init skipped or failed: %s", e, extra={})
    logger.info("api_gateway startup", extra={"service": "fastapi_gateway"})
    yield
    logger.info("api_gateway shutdown", extra={})


app = FastAPI(
    title="Amazon Research API Gateway",
    description="Minimal gateway for dashboard and workspace data. Reuses existing service layers.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS: if GATEWAY_CORS_ORIGINS is set, use those specific origins (production);
# otherwise fall back to allow-all for local development.
_cors_origins = os.environ.get("GATEWAY_CORS_ORIGINS", "").strip()
_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()] if _cors_origins else []

if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )
else:
    # Development fallback: allow all origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.exception_handler(Exception)
def global_exception_handler(request, exc):
    """Safe JSON error response; no secret leakage."""
    path = getattr(getattr(request, "url", None), "path", "") or ""
    logger.warning("api_gateway unhandled error: %s", exc, extra={"path": path})
    return JSONResponse(status_code=500, content={"detail": "internal_error"})

app.include_router(health.router, tags=["health"])
app.include_router(workspaces.router, prefix="/api/workspaces", tags=["workspaces"])
app.include_router(discovery.router, prefix="/api/workspaces/{workspace_id}/discovery", tags=["discovery"])
app.include_router(copilot.router, prefix="/api/copilot", tags=["copilot"])
