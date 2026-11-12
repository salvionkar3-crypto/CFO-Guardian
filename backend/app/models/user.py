"""User Model

Represents registered operators, business owners, and financial controllers.
Enforces bcrypt hashed passwords, role-based access, and account status.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="OWNER", nullable=False)  # OWNER, ADMIN, AUDITOR, VIEWER
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    businesses = relationship("Business", back_populates="owner", cascade="all, delete-orphan")
    payment_drafts = relationship("PaymentDraft", foreign_keys="[PaymentDraft.created_by_id]", back_populates="created_by")
    approved_payment_drafts = relationship("PaymentDraft", foreign_keys="[PaymentDraft.approved_by_id]", back_populates="approved_by")
    secondary_approved_payment_drafts = relationship("PaymentDraft", foreign_keys="[PaymentDraft.secondary_approved_by_id]", back_populates="secondary_approved_by")
    payment_approvals = relationship("PaymentApproval", back_populates="approved_by")
    security_alerts_resolved = relationship("SecurityAlert", back_populates="resolved_by")
    audit_logs = relationship("AuditLog", back_populates="user")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
