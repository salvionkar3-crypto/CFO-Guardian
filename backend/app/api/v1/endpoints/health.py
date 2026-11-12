"""System Health and Diagnostics Endpoint
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db, check_db_connection
from app.core.config import settings
from app.schemas.health import HealthResponse, ServiceStatus
from app.services.paypal_service import PayPalService

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Comprehensive health check for DB connectivity, PayPal status, and OpenAI configuration."""
    db_status = check_db_connection()

    # PayPal check
    paypal_status_data = await PayPalService.verify_credentials()
    paypal_status = ServiceStatus(
        configured=paypal_status_data["configured"],
        status=paypal_status_data["status"],
        details=paypal_status_data.get("details"),
    )

    # OpenAI check
    openai_configured = bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"))
    openai_status = ServiceStatus(
        configured=openai_configured,
        status="ready" if openai_configured else "unconfigured",
        details="Key present and loaded" if openai_configured else "Set OPENAI_API_KEY in .env to enable deep LLM reasoning",
    )

    overall_status = "healthy" if db_status["status"] == "connected" else "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status,
        paypal=paypal_status,
        openai=openai_status,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )

