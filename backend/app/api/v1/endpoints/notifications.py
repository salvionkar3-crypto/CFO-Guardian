"""Notifications Endpoints - Multi-Tenant Scoped
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_business, get_current_user
from app.models.business import Business
from app.models.user import User
from app.services.notification_service import NotificationService
from app.schemas.notification import NotificationResponse, UnreadCountResponse, MarkReadResponse

router = APIRouter()


@router.get("", response_model=List[NotificationResponse])
def get_notifications(
    is_read: Optional[bool] = Query(None, description="Filter by read status (true/false)"),
    category: Optional[str] = Query(None, description="Filter by category (e.g. HIGH_RISK_DETECTED)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Retrieves notifications strictly scoped to the authenticated tenant."""
    notifications = NotificationService.get_notifications(
        db=db,
        business_id=business.id,
        is_read=is_read,
        category=category,
        limit=limit,
        offset=offset,
    )
    return notifications


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Returns the count of unread notifications for the business badge."""
    count = NotificationService.get_unread_count(db=db, business_id=business.id)
    return UnreadCountResponse(unread_count=count)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Marks an individual notification as read."""
    notif = NotificationService.mark_as_read(
        db=db,
        notification_id=notification_id,
        business_id=business.id,
    )
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification #{notification_id} not found in this business account.",
        )
    return notif


@router.post("/read-all", response_model=MarkReadResponse)
def mark_all_notifications_read(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Marks all unread notifications for the authenticated business as read."""
    count = NotificationService.mark_all_as_read(db=db, business_id=business.id)
    return MarkReadResponse(success=True, marked_count=count)

