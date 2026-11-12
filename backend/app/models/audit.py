"""Audit Log Model

Maintains an immutable historical ledger of every financial, security,
and payment action across the 8-stage pipeline:
Understand -> Analyze -> Investigate -> Decide -> Approve -> Pay -> Monitor -> Explain.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    decision_id = Column(Integer, nullable=True, index=True)

    # Pipeline Stage
    stage = Column(String(50), nullable=False, index=True)  # UNDERSTAND, ANALYZE, INVESTIGATE, DECIDE, APPROVE, PAY, MONITOR, EXPLAIN

    # Actor: AI_CFO, GUARDIAN_AI, PAYMENT_AGENT, USER, SYSTEM
    actor = Column(String(50), nullable=False)
    action = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    rationale = Column(Text, nullable=True)  # Explainability reasoning
    ip_address = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    business = relationship("Business", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
