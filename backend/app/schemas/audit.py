"""Audit Log and Explainability Schemas
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    decision_id: Optional[int] = None
    stage: str
    actor: str
    action: str
    summary: str
    details: Optional[str] = None
    rationale: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime


class ApproverDetail(BaseModel):
    step: int
    user_id: Optional[int] = None
    name: str
    email: Optional[str] = None
    role: Optional[str] = None
    approved_at: datetime
    notes: Optional[str] = None


class RejectionDetail(BaseModel):
    user_id: Optional[int] = None
    name: str
    email: Optional[str] = None
    rejected_at: datetime
    reason: str


class ApprovalDetails(BaseModel):
    status: str
    requires_dual_approval: bool = False
    approvers: List[ApproverDetail] = []
    rejected_by: Optional[RejectionDetail] = None


class ProviderStatusDetails(BaseModel):
    provider: str = "PayPal REST API"
    mode: str = "sandbox"
    order_id: Optional[str] = None
    capture_id: Optional[str] = None
    status: str = "NOT_INITIATED"
    reconciled_at: Optional[datetime] = None
    settlement_amount: Optional[str] = None


class ExplainabilityReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision_id: int
    title: str
    vendor: str
    amount: float
    currency: str
    current_status: str
    cfo_reasoning: Optional[str] = None
    guardian_security_summary: Optional[str] = None
    audit_trail: List[AuditLogItem] = []

    # 6 Core Transparent Explainability Answers
    what_happened: str
    why_flagged: str
    evidence_detected: List[str] = []
    action_taken: str
    approval_details: ApprovalDetails
    final_provider_status: ProviderStatusDetails
