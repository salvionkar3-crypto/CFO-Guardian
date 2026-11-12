"""Webhook Pydantic Schemas
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class WebhookProcessResponse(BaseModel):
    status: str
    duplicate: bool
    event_id: str
    event_type: str
    result: Optional[Dict[str, Any]] = None


class WebhookEventItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: Optional[int] = None
    event_type: str
    event_id: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    payload: str

