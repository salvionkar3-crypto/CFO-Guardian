"""API Router V1 Aggregator
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    cfo,
    cfo_chat,
    guardian,
    payments,
    audit,
    analytics,
    notifications,
    webhooks,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Tenant Management"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Financial Analytics"])
api_router.include_router(cfo.router, prefix="/cfo", tags=["AI CFO Metrics & Invoices"])
api_router.include_router(cfo_chat.router, prefix="/cfo/chat", tags=["AI CFO Natural Language Consultation"])
api_router.include_router(guardian.router, prefix="/guardian", tags=["Guardian AI"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payment Agent (PayPal)"])
api_router.include_router(audit.router, prefix="/audit", tags=["Explainability & Audit"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications & Alerts"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["PayPal Webhooks"])
