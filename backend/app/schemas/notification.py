"""Notification Pydantic Schemas
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    user_id: Optional[int] = None
    category: str
    severity: str
    title: str
    message: str
    payment_draft_id: Optional[int] = None
    transaction_id: Optional[int] = None
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkReadResponse(BaseModel):
    success: bool
    marked_count: int

