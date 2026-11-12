"""Notification Model

Stores real-time system and security alerts:
- High-risk payment detected
- Payment awaiting approval (step 1 or step 2)
- Payment approved
- Payment rejected
- Payment completed
- Payment failed
- Unusual financial activity
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Category: HIGH_RISK_DETECTED, PAYMENT_AWAITING_APPROVAL, PAYMENT_APPROVED, PAYMENT_REJECTED,
    #           PAYMENT_COMPLETED, PAYMENT_FAILED, UNUSUAL_FINANCIAL_ACTIVITY
    category = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), default="INFO", nullable=False)  # INFO, LOW, MEDIUM, HIGH, CRITICAL

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    payment_draft_id = Column(Integer, ForeignKey("payment_drafts.id", ondelete="SET NULL"), nullable=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True)

    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)

    # Relationships
    business = relationship("Business", back_populates="notifications")
    user = relationship("User")
    payment_draft = relationship("PaymentDraft")
    transaction = relationship("Transaction")

