"""Vendor Model

Represents registered payees, contractors, and SaaS providers.
Tracks trust score, verification state, and cumulative payouts.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    website = Column(String(255), nullable=True)

    # Status: ACTIVE, BLOCKED, UNDER_REVIEW
    status = Column(String(50), default="ACTIVE", nullable=False)
    trust_score = Column(Float, default=85.0, nullable=False)  # 0.0 to 100.0

    bank_or_paypal_email = Column(String(255), nullable=True)
    total_paid = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    business = relationship("Business", back_populates="vendors")
    payment_drafts = relationship("PaymentDraft", back_populates="vendor")
    transactions = relationship("Transaction", back_populates="vendor")
