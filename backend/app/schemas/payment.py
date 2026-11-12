"""Secure Payment Management Schemas

Defines contracts for:
- Vendor selection and creation
- Payment draft lifecycle (DRAFT -> RISK_REVIEWED -> AWAITING_APPROVAL -> APPROVED -> PROVIDER_PENDING -> COMPLETED)
- Server-side payee, amount, currency, and purpose validations
- Idempotency key tracking and approval invalidation
- Payment execution via Simulated Provider and PayPal Sandbox
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict


# ==========================================
# Vendor Schemas
# ==========================================

class VendorCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Vendor business name")
    email: EmailStr = Field(..., description="Vendor billing email")
    website: Optional[str] = Field(None, max_length=255)
    bank_or_paypal_email: Optional[EmailStr] = Field(None, description="Disbursement PayPal or bank email")


class VendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    name: str
    email: str
    website: Optional[str] = None
    status: str
    trust_score: float
    bank_or_paypal_email: Optional[str] = None
    total_paid: float
    created_at: datetime


# ==========================================
# Payment Draft Schemas
# ==========================================

class PaymentDraftCreateRequest(BaseModel):
    vendor_id: Optional[int] = Field(None, description="ID of existing vendor")
    new_vendor: Optional[VendorCreateRequest] = Field(None, description="Create new vendor inline")
    title: str = Field(..., min_length=3, max_length=255, description="Short title for payment")
    amount: float = Field(..., gt=0.01, description="Positive payment amount")
    currency: str = Field("USD", pattern="^(USD|EUR|GBP|INR|CAD|AUD)$", description="ISO 4217 Currency Code")
    category: str = Field("General", min_length=2, max_length=100)
    purpose: str = Field(..., min_length=3, max_length=255, description="Explicit commercial purpose of payment")
    invoice_number: Optional[str] = Field(None, max_length=100)
    invoice_url: Optional[str] = Field(None, max_length=500)
    idempotency_key: Optional[str] = Field(None, max_length=128, description="Client idempotency key")
    auto_run_risk_scan: bool = Field(True, description="Automatically trigger Guardian risk evaluation")


class PaymentDraftUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    amount: Optional[float] = Field(None, gt=0.01)
    currency: Optional[str] = Field(None, pattern="^(USD|EUR|GBP|INR|CAD|AUD)$")
    category: Optional[str] = None
    purpose: Optional[str] = Field(None, min_length=3, max_length=255)
    invoice_number: Optional[str] = None
    invoice_url: Optional[str] = None


class PaymentDraftApproveRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=500)
    expected_details_hash: Optional[str] = Field(None, description="Hash of details when viewed by user to prevent race edits")
    dual_approval_override: bool = Field(False, description="Elevated dual-control authorization flag")


class PaymentDraftRejectRequest(BaseModel):
    reason: str = Field(..., min_length=2, max_length=500, description="Mandatory executive reason for rejection")


class PaymentApprovalItemResponse(BaseModel):
    id: int
    approved_by_id: int
    approved_by_name: Optional[str] = None
    status: str
    approval_role: str
    notes: Optional[str] = None
    details_hash: Optional[str] = None
    approved_at: datetime
    expires_at: Optional[datetime] = None


class PaymentDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    vendor_id: int
    vendor_name: str
    vendor_email: str
    title: str
    amount: float
    currency: str
    category: str
    purpose: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_url: Optional[str] = None
    description: Optional[str] = None
    status: str
    cfo_recommendation: str
    cfo_rationale: Optional[str] = None
    budget_impact_pct: float
    runway_impact_days: int
    details_hash: Optional[str] = None
    idempotency_key: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_by_id: Optional[int] = None
    approved_by_name: Optional[str] = None
    expires_at: Optional[datetime] = None
    requires_dual_approval: bool = False
    secondary_approved_at: Optional[datetime] = None
    secondary_approved_by_id: Optional[int] = None
    secondary_approved_by_name: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    risk_assessment: Optional[Dict[str, Any]] = None
    policy_eligibility: Optional[Dict[str, Any]] = None
    approvals: Optional[List[PaymentApprovalItemResponse]] = None


# ==========================================
# Payment Execution & Simulation Schemas
# ==========================================

class ExecutePaymentRequest(BaseModel):
    draft_id: int
    idempotency_key: Optional[str] = Field(None, max_length=128)
    payment_method: str = Field("SIMULATED_PROVIDER", description="SIMULATED_PROVIDER or PAYPAL_SANDBOX")


class ExecutePaymentResponse(BaseModel):
    transaction_id: int
    draft_id: int
    status: str  # PROVIDER_PENDING, COMPLETED, FAILED
    amount: float
    currency: str
    recipient_email: str
    provider_reference: str
    payment_method: str
    is_sandbox: bool
    approval_url: Optional[str] = None
    settled_at: Optional[datetime] = None
    message: str


# ==========================================
# PayPal REST API Schemas
# ==========================================

class PayPalConfigResponse(BaseModel):
    configured: bool
    mode: str
    base_url: str
    client_id_preview: Optional[str] = None
    status: str
    details: str


class PayPalCreateOrderDraftRequest(BaseModel):
    draft_id: int
    return_url: Optional[str] = "http://localhost:3000/dashboard/payments/success"
    cancel_url: Optional[str] = "http://localhost:3000/dashboard/payments/cancel"
    idempotency_key: Optional[str] = None


class PayPalOrderDraftResponse(BaseModel):
    transaction_id: int
    draft_id: int
    paypal_order_id: str
    status: str
    is_sandbox: bool
    approval_url: Optional[str] = None
    amount: float
    currency: str
    recipient_email: str


# ==========================================
# Legacy PayPal Orders (Backwards Compatibility)
# ==========================================

class CreatePaymentOrderRequest(BaseModel):
    decision_id: int
    return_url: Optional[str] = "http://localhost:3000/dashboard/payments/success"
    cancel_url: Optional[str] = "http://localhost:3000/dashboard/payments/cancel"


class PayPalOrderResponse(BaseModel):
    transaction_id: int
    decision_id: int
    paypal_order_id: str
    status: str
    is_sandbox: bool
    approval_url: Optional[str] = None
    amount: float
    currency: str
    recipient_email: str


class CapturePaymentOrderRequest(BaseModel):
    transaction_id: int
    paypal_order_id: str


class PaymentCaptureResponse(BaseModel):
    transaction_id: int
    paypal_order_id: str
    paypal_capture_id: Optional[str] = None
    status: str
    is_sandbox: bool
    amount: float
    currency: str
    details: Optional[Dict[str, Any]] = None


class TransactionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    vendor_id: Optional[int] = None
    payment_draft_id: Optional[int] = None
    transaction_type: str
    amount: float
    currency: str
    status: str
    category: str
    description: Optional[str] = None
    is_recurring: bool
    recurring_frequency: Optional[str] = None
    idempotency_key: Optional[str] = None
    payment_method: str
    paypal_order_id: Optional[str] = None
    paypal_capture_id: Optional[str] = None
    settled_at: Optional[datetime] = None
    created_at: datetime


# ==========================================
# Payment Decision Room Schemas
# ==========================================

class DecisionRoomOverview(BaseModel):
    draft_id: int
    title: str
    vendor_id: int
    vendor_name: str
    vendor_email: str
    vendor_status: str
    amount: float
    currency: str
    invoice_number: Optional[str] = None
    invoice_url: Optional[str] = None
    purpose: Optional[str] = None
    category: str
    status: str
    created_at: datetime
    updated_at: datetime
    details_hash: Optional[str] = None
    idempotency_key: Optional[str] = None


class DecisionRoomRiskSignal(BaseModel):
    id: str
    name: str
    severity: str
    score_impact: float
    description: str
    evidence: str


class DecisionRoomRiskAssessment(BaseModel):
    id: Optional[int] = None
    risk_score: float
    risk_level: str
    verdict: str
    recommended_action: str
    plain_explanation: str
    signals: List[DecisionRoomRiskSignal] = []
    supporting_evidence: List[str] = []
    missing_information: List[str] = []
    flags: List[str] = []
    verification_hash: Optional[str] = None
    anomaly_detected: bool = False
    vendor_verified: bool = False
    is_duplicate_invoice: bool = False
    created_at: Optional[str] = None


class DecisionRoomAiRecommendation(BaseModel):
    why_risky: str
    verified_facts: List[str] = []
    cash_flow_impact: str
    required_verifications: List[str] = []
    recommended_reviewer_action: str
    is_ai_generated: bool = False
    disclaimer: str = (
        "Guardian AI recommendations are advisory financial analysis. "
        "Official authorization and execution require explicit human approval."
    )


class DecisionRoomCommitmentItem(BaseModel):
    vendor_name: str
    category: str
    amount: float
    frequency: str


class DecisionRoomCashFlowImpact(BaseModel):
    available_cash_before: float
    payment_amount: float
    projected_cash_after: float
    percentage_cash_consumed: float
    monthly_budget: float
    monthly_spent_before: float
    projected_monthly_spent: float
    percentage_budget_consumed: float
    remaining_budget_before: float
    projected_remaining_budget: float
    runway_impact_days: int
    projected_runway_months: float
    commitments_monthly_total: float
    active_commitments_count: int
    commitments_sample: List[DecisionRoomCommitmentItem] = []
    calculation_notes: str


class DecisionRoomApprover(BaseModel):
    step: int
    user_id: Optional[int] = None
    name: str
    email: Optional[str] = None
    role: Optional[str] = None
    approved_at: datetime
    notes: Optional[str] = None
    details_hash: Optional[str] = None


class DecisionRoomApprovalWorkflow(BaseModel):
    can_approve: bool
    mandatory_block: bool
    requires_dual_approval: bool
    current_step: int
    total_steps: int
    step_name: str
    reason: str
    recommended_action: str
    primary_approver: Optional[DecisionRoomApprover] = None
    secondary_approver: Optional[DecisionRoomApprover] = None
    approval_history: List[DecisionRoomApprover] = []
    rejection_reason: Optional[str] = None
    details_hash: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_expired: bool = False


class DecisionRoomAuditItem(BaseModel):
    id: int
    stage: str
    actor: str
    action: str
    summary: str
    details: Optional[str] = None
    rationale: Optional[str] = None
    timestamp: datetime


class DecisionRoomPayPalStatus(BaseModel):
    is_configured: bool
    mode: str = "sandbox"
    client_id_preview: Optional[str] = None
    order_id: Optional[str] = None
    capture_id: Optional[str] = None
    approval_url: Optional[str] = None
    transaction_status: Optional[str] = None
    settled_at: Optional[datetime] = None


class PaymentDecisionRoomResponse(BaseModel):
    overview: DecisionRoomOverview
    risk_assessment: DecisionRoomRiskAssessment
    ai_recommendation: DecisionRoomAiRecommendation
    cash_flow_impact: DecisionRoomCashFlowImpact
    approval_workflow: DecisionRoomApprovalWorkflow
    audit_timeline: List[DecisionRoomAuditItem] = []
    paypal_status: DecisionRoomPayPalStatus


class PaymentDraftHoldRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000, description="Reason for holding payment")


class PaymentDraftReviewRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000, description="Reason for requesting human review")


