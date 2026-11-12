"""Business and Business Settings Models

Encapsulates company treasury, multi-tenant boundaries, and governance policies.
Strict Tenant Isolation: Every business record is isolated by owner_id and business_id.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    legal_name = Column(String(255), nullable=True)
    currency = Column(String(10), default="USD", nullable=False)
    tax_id = Column(String(100), nullable=True)

    # Treasury balances & runway tracking
    total_balance = Column(Float, default=125000.0, nullable=False)
    monthly_budget = Column(Float, default=35000.0, nullable=False)
    monthly_spent = Column(Float, default=0.0, nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="businesses")
    settings = relationship("BusinessSettings", back_populates="business", uselist=False, cascade="all, delete-orphan")
    vendors = relationship("Vendor", back_populates="business", cascade="all, delete-orphan")
    payment_drafts = relationship("PaymentDraft", back_populates="business", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="business", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="business", cascade="all, delete-orphan")
    security_alerts = relationship("SecurityAlert", back_populates="business", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="business", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="business", cascade="all, delete-orphan")
    webhook_events = relationship("WebhookEvent", back_populates="business", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="business", cascade="all, delete-orphan")


class BusinessSettings(Base):
    __tablename__ = "business_settings"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Financial Guardrails
    auto_approve_threshold = Column(Float, default=250.0, nullable=False)
    max_single_payment_limit = Column(Float, default=5000.0, nullable=False)
    require_dual_approval_above = Column(Float, default=1000.0, nullable=False)
    risk_tolerance_level = Column(String(50), default="MEDIUM", nullable=False)  # LOW, MEDIUM, HIGH
    approval_validity_hours = Column(Float, default=24.0, nullable=False)
    block_critical_risk = Column(Boolean, default=True, nullable=False)

    notification_email = Column(String(255), nullable=True)
    enable_paypal_sandbox = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    business = relationship("Business", back_populates="settings")
