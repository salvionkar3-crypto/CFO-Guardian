"""Database Connection and Session Management

Supports PostgreSQL (production standard via psycopg) and SQLite (zero-friction local dev).
Includes health check verification with ping and connection pooling.
"""

from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings
from app.core.logging_config import logger

Base = declarative_base()

# Configure engine with robust pooling and pre-ping
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped database session and guarantees closure."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> dict:
    """Verifies live database connectivity and returns status metadata."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_type = "postgresql" if "postgres" in settings.DATABASE_URL else "sqlite"
        return {
            "status": "connected",
            "type": db_type,
            "error": None,
        }
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        return {
            "status": "disconnected",
            "type": "unknown",
            "error": str(exc),
        }

