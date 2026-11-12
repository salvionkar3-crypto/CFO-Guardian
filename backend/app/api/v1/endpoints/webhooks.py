"""PayPal Webhook Endpoints
"""

from typing import List, Optional
import json
from fastapi import APIRouter, Request, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_business
from app.models.business import Business
from app.models.webhook import WebhookEvent
from app.services.webhook_service import PayPalWebhookService, WebhookVerificationError
from app.schemas.webhook import WebhookProcessResponse, WebhookEventItem

router = APIRouter()


@router.post("/paypal", response_model=WebhookProcessResponse)
async def receive_paypal_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Ingests, verifies signature, deduplicates, and processes inbound PayPal webhooks.
    
    PayPal requires HTTP 200/204 response upon safe receipt.
    Unverified signatures are strictly rejected with HTTP 400.
    """
    raw_body = await request.body()
    try:
        body_json = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        )

    headers = dict(request.headers)

    try:
        res = await PayPalWebhookService.process_webhook(
            db=db,
            headers=headers,
            raw_body=raw_body,
            body_json=body_json,
        )
        return WebhookProcessResponse(
            status=res.get("status", "PROCESSED"),
            duplicate=res.get("duplicate", False),
            event_id=res.get("event_id", ""),
            event_type=res.get("event_type", ""),
            result=res.get("result"),
        )
    except WebhookVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing error: {str(e)}",
        )


@router.get("/events", response_model=List[WebhookEventItem])
def list_webhook_events(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (RECEIVED, PROCESSED, FAILED)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Lists received webhook events for audit inspection."""
    query = db.query(WebhookEvent).filter(
        (WebhookEvent.business_id == business.id) | (WebhookEvent.business_id.is_(None))
    )
    if status_filter:
        query = query.filter(WebhookEvent.status == status_filter.upper())

    events = query.order_by(WebhookEvent.created_at.desc()).offset(offset).limit(limit).all()
    return events

