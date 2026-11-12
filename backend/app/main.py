"""Guardian CFO - FastAPI Application Entrypoint

Fintech architecture featuring:
- AI CFO Financial Assistant
- Guardian AI Security & Risk Detection
- PayPal REST API Payment Agent
- Explainability & Audit Engine
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging_config import setup_logging, logger
from app.db.base import init_db
from app.db.session import SessionLocal
from app.db.seed import seed_demo_data
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    setup_logging(settings.LOG_LEVEL)
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    try:
        init_db()
        logger.info("Database schema verified and initialized.")
        # Ensure demo ecosystem is seeded
        with SessionLocal() as db:
            seed_demo_data(db)
        logger.info("Demo business ecosystem ready.")
    except Exception as exc:
        logger.error(f"Database initialization warning: {exc}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="The AI CFO That Thinks Before It Pays - Secure Financial Intelligence & PayPal Agent",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_and_logging(request: Request, call_next):
    """Performance timing and request audit middleware."""
    if request.method == "OPTIONS":
        return await call_next(request)

    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Process-Time"] = f"{duration_ms}ms"

    if request.url.path not in ("/api/v1/health", "/"):
        logger.info(f"{request.method} {request.url.path} - status {response.status_code} in {duration_ms}ms")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ensures unhandled exceptions produce clean structured JSON instead of HTML traces."""
    logger.error(f"Unhandled error processing {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred. The incident has been recorded in system audit logs.",
            "path": request.url.path,
        },
    )


# Mount versioned API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    """Service discovery root endpoint."""
    return {
        "project": settings.PROJECT_NAME,
        "tagline": "The AI CFO That Thinks Before It Pays",
        "version": settings.VERSION,
        "status": "operational",
        "docs_url": f"{settings.API_V1_STR}/docs",
        "health_check": f"{settings.API_V1_STR}/health",
        "workflow": [
            "UNDERSTAND",
            "ANALYZE",
            "INVESTIGATE",
            "DECIDE",
            "APPROVE",
            "PAY",
            "MONITOR",
            "EXPLAIN",
        ],
    }

