"""Webhook Events Model

Logs inbound webhooks (e.g. PayPal payment authorizations, disputes, capture events)
for asynchronous idempotent processing and audit trails.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=True, index=True)

    event_type = Column(String(100), nullable=False, index=True)
    event_id = Column(String(100), nullable=False, index=True)
    payload = Column(Text, nullable=False)

    # Status: RECEIVED, PROCESSED, FAILED
    status = Column(String(50), default="RECEIVED", nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    business = relationship("Business", back_populates="webhook_events")
