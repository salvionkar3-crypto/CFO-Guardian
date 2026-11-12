"""Guardian AI Security Models

Defines:
- RiskAssessment: Fraud scores (0-100), heuristic flags, and tamper hashes
- SecurityAlert: Real-time fraud and security notifications requiring resolution
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_draft_id = Column(Integer, ForeignKey("payment_drafts.id", ondelete="CASCADE"), nullable=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True)

    risk_score = Column(Float, nullable=False, default=0.0)  # 0.0 to 100.0
    risk_level = Column(String(50), nullable=False, default="LOW")  # LOW, MEDIUM, HIGH, CRITICAL
    verdict = Column(String(50), nullable=False, default="REQUIRES_MANUAL_REVIEW")  # SAFE_TO_PAY, REQUIRES_MANUAL_REVIEW, BLOCKED

    flags = Column(Text, nullable=True)  # JSON serialized list of anomaly descriptions
    risk_signals = Column(Text, nullable=True)  # JSON serialized list of detailed signal objects
    supporting_evidence = Column(Text, nullable=True)  # JSON serialized list of evidence items
    missing_information = Column(Text, nullable=True)  # JSON serialized list of missing data
    recommended_action = Column(String(100), nullable=True)  # SAFE_TO_PAY, REQUIRES_MANUAL_REVIEW, REJECT_AND_BLOCK
    plain_explanation = Column(Text, nullable=True)  # Plain language executive rationale
    anomaly_detected = Column(Boolean, default=False, nullable=False)
    vendor_verified = Column(Boolean, default=False, nullable=False)
    is_duplicate_invoice = Column(Boolean, default=False, nullable=False)
    verification_hash = Column(String(128), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    business = relationship("Business", back_populates="risk_assessments")
    payment_draft = relationship("PaymentDraft", back_populates="risk_assessments")
    transaction = relationship("Transaction", back_populates="risk_assessments")


class SecurityAlert(Base):
    __tablename__ = "security_alerts"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)

    severity = Column(String(50), default="MEDIUM", nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), default="OPEN", nullable=False, index=True)  # OPEN, INVESTIGATING, RESOLVED, DISMISSED

    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    business = relationship("Business", back_populates="security_alerts")
    resolved_by = relationship("User", back_populates="security_alerts_resolved")
