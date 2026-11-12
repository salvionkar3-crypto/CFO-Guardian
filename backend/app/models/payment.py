"""Payment Models

Defines the end-to-end payment execution lifecycle:
- PaymentDraft: Invoiced amount, CFO recommendation, and runway impact
- PaymentApproval: Dual sign-off records
- Transaction: PayPal REST API order and capture records
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class PaymentDraft(Base):
    __tablename__ = "payment_drafts"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    category = Column(String(100), default="General", nullable=False)

    invoice_number = Column(String(100), nullable=True)
    invoice_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    purpose = Column(String(255), nullable=True)
    idempotency_key = Column(String(128), index=True, nullable=True)
    details_hash = Column(String(64), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    expires_at = Column(DateTime, nullable=True)
    requires_dual_approval = Column(Boolean, default=False, nullable=False)
    secondary_approved_at = Column(DateTime, nullable=True)
    secondary_approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    rejection_reason = Column(Text, nullable=True)

    # Status: DRAFT, RISK_REVIEWED, AWAITING_APPROVAL, APPROVED, PROVIDER_PENDING, COMPLETED, REJECTED, FAILED, EXPIRED, REVIEW_REQUIRED
    status = Column(String(50), default="DRAFT", nullable=False, index=True)

    # AI CFO Analysis Results
    cfo_recommendation = Column(String(50), default="UNDER_REVIEW", nullable=False)
    cfo_rationale = Column(Text, nullable=True)
    budget_impact_pct = Column(Float, default=0.0)
    runway_impact_days = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    business = relationship("Business", back_populates="payment_drafts")
    vendor = relationship("Vendor", back_populates="payment_drafts")
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="payment_drafts")
    approved_by = relationship("User", foreign_keys=[approved_by_id], back_populates="approved_payment_drafts")
    secondary_approved_by = relationship("User", foreign_keys=[secondary_approved_by_id], back_populates="secondary_approved_payment_drafts")
    approvals = relationship("PaymentApproval", back_populates="payment_draft", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="payment_draft", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="payment_draft")

    @property
    def vendor_name(self) -> str:
        return self.vendor.name if self.vendor else "Unknown Vendor"

    @property
    def vendor_email(self) -> str:
        return self.vendor.email if self.vendor else ""


class PaymentApproval(Base):
    __tablename__ = "payment_approvals"

    id = Column(Integer, primary_key=True, index=True)
    payment_draft_id = Column(Integer, ForeignKey("payment_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(String(50), nullable=False)  # APPROVED, REJECTED
    approval_role = Column(String(50), default="PRIMARY_APPROVER", nullable=False)  # PRIMARY_APPROVER, SECONDARY_APPROVER, REJECTION
    details_hash = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)
    approved_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    payment_draft = relationship("PaymentDraft", back_populates="approvals")
    approved_by = relationship("User", back_populates="payment_approvals")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_draft_id = Column(Integer, ForeignKey("payment_drafts.id", ondelete="SET NULL"), nullable=True, index=True)

    # Transaction Type: "INCOME" (Revenue) or "EXPENSE" (Expenditure)
    transaction_type = Column(String(20), default="EXPENSE", nullable=False, index=True)

    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    # Status: PENDING, APPROVED, COMPLETED, FAILED, CANCELLED
    status = Column(String(50), default="COMPLETED", nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    description = Column(String(255), nullable=True)

    # Recurring expense flags
    is_recurring = Column(Boolean, default=False, nullable=False, index=True)
    recurring_frequency = Column(String(50), nullable=True)  # MONTHLY, QUARTERLY, ANNUAL, WEEKLY

    # Payment Execution Tracking
    idempotency_key = Column(String(128), nullable=True, index=True)
    payment_method = Column(String(50), default="PAYPAL_SANDBOX", nullable=False)

    # PayPal REST API Identifiers
    paypal_order_id = Column(String(100), nullable=True, index=True)
    paypal_capture_id = Column(String(100), nullable=True, index=True)
    is_sandbox = Column(Boolean, default=True, nullable=False)
    raw_paypal_response = Column(Text, nullable=True)

    settled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    business = relationship("Business", back_populates="transactions")
    vendor = relationship("Vendor", back_populates="transactions")
    payment_draft = relationship("PaymentDraft", back_populates="transactions")
    risk_assessments = relationship("RiskAssessment", back_populates="transaction")


# Backwards compatibility alias
PaymentTransaction = Transaction
