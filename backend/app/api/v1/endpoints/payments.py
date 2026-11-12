"""Payment Management Endpoints (Secure Payment Management System & PayPal Sandbox)

Implements the complete Payment Lifecycle:
DRAFT -> RISK_REVIEWED -> AWAITING_APPROVAL -> APPROVED -> PROVIDER_PENDING -> COMPLETED
(Also REJECTED, FAILED, EXPIRED, REVIEW_REQUIRED)

Key Security Guarantees:
1. Multi-Tenant isolation: All drafts, transactions, and vendors scoped strictly to current_business.id.
2. Server-side validation: Payee, amount (>0), supported currency whitelist, and explicit purpose.
3. Idempotency Keying: Prevents duplicate draft submissions and double-charge execution.
4. Tamper Detection & Approval Invalidation: SHA-256 details_hash ensures any modification after
   review or approval immediately revokes approval and flags REVIEW_REQUIRED.
5. Provider Confirmation Rule: Status is set to PROVIDER_PENDING before provider confirmation,
   and only marked COMPLETED once the payment provider acknowledges settlement.
6. Guardrail: Direct AI chat cannot execute payments; explicit user review and approval are mandatory.
"""

import hashlib
import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
import httpx

from app.db.session import get_db
from app.api.deps import get_current_business, get_current_user
from app.models.user import User
from app.models.business import Business
from app.models.vendor import Vendor
from app.models.payment import PaymentDraft, PaymentApproval, Transaction
from app.models.guardian import RiskAssessment, SecurityAlert
from app.models.audit import AuditLog
from app.services.guardian_service import GuardianRiskEngine, GuardianRiskConfig
from app.services.audit_service import AuditService
from app.services.policy_engine import PaymentPolicyEngine
from app.schemas.payment import (
    VendorCreateRequest,
    VendorResponse,
    PaymentDraftCreateRequest,
    PaymentDraftUpdateRequest,
    PaymentDraftApproveRequest,
    PaymentDraftRejectRequest,
    PaymentApprovalItemResponse,
    PaymentDraftResponse,
    ExecutePaymentRequest,
    ExecutePaymentResponse,
    CreatePaymentOrderRequest,
    PayPalOrderResponse,
    CapturePaymentOrderRequest,
    PaymentCaptureResponse,
    TransactionItemResponse,
    PayPalConfigResponse,
    PayPalCreateOrderDraftRequest,
    PayPalOrderDraftResponse,
    PaymentDecisionRoomResponse,
    PaymentDraftHoldRequest,
    PaymentDraftReviewRequest,
)
from app.services.decision_room_service import DecisionRoomService
from app.services.paypal_service import (
    PayPalService,
    PayPalConfigurationError,
    PayPalAPIError,
)
from app.core.config import settings

router = APIRouter()


# ==============================================================================
# Helper Functions
# ==============================================================================

def compute_details_hash(
    vendor_id: int,
    amount: float,
    currency: str,
    purpose: Optional[str],
    invoice_number: Optional[str] = None,
) -> str:
    """Computes a cryptographic SHA-256 fingerprint of core payment commitment fields."""
    return PaymentPolicyEngine.compute_details_hash(
        vendor_id=vendor_id,
        amount=amount,
        currency=currency,
        purpose=purpose,
        invoice_number=invoice_number,
    )


def format_draft_response(draft: PaymentDraft, db: Session) -> PaymentDraftResponse:
    """Formats a PaymentDraft SQLAlchemy instance into a rich PaymentDraftResponse."""
    # Check expiration dynamically
    if draft.business:
        PaymentPolicyEngine.check_and_apply_expiration(db, draft, draft.business)

    assessment = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.payment_draft_id == draft.id)
        .order_by(RiskAssessment.created_at.desc())
        .first()
    )
    risk_dict = None
    if assessment:
        try:
            signals = json.loads(assessment.risk_signals) if isinstance(assessment.risk_signals, str) else assessment.risk_signals
        except Exception:
            signals = []
        try:
            evidence = json.loads(assessment.supporting_evidence) if isinstance(assessment.supporting_evidence, str) else assessment.supporting_evidence
        except Exception:
            evidence = []
        try:
            missing = json.loads(assessment.missing_information) if isinstance(assessment.missing_information, str) else assessment.missing_information
        except Exception:
            missing = []

        risk_dict = {
            "id": assessment.id,
            "risk_score": assessment.risk_score,
            "risk_level": assessment.risk_level,
            "verdict": assessment.verdict,
            "recommended_action": assessment.recommended_action,
            "plain_explanation": assessment.plain_explanation,
            "risk_signals": signals,
            "supporting_evidence": evidence,
            "missing_information": missing,
            "vendor_verified": assessment.vendor_verified,
            "is_duplicate_invoice": assessment.is_duplicate_invoice,
            "verification_hash": assessment.verification_hash,
            "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
        }

    # Policy determination
    policy_dict = None
    if draft.business:
        policy_dict = PaymentPolicyEngine.evaluate_approval_eligibility(db, draft, draft.business)

    # Approvals list
    approval_items = []
    if draft.approvals:
        for ap in sorted(draft.approvals, key=lambda x: x.approved_at or datetime.min):
            approval_items.append(
                PaymentApprovalItemResponse(
                    id=ap.id,
                    approved_by_id=ap.approved_by_id,
                    approved_by_name=ap.approved_by.full_name if ap.approved_by else None,
                    status=ap.status,
                    approval_role=ap.approval_role or "PRIMARY_APPROVER",
                    notes=ap.notes,
                    details_hash=ap.details_hash,
                    approved_at=ap.approved_at,
                    expires_at=ap.expires_at,
                )
            )

    approved_by_name = draft.approved_by.full_name if draft.approved_by else None
    secondary_approved_by_name = draft.secondary_approved_by.full_name if draft.secondary_approved_by else None

    return PaymentDraftResponse(
        id=draft.id,
        business_id=draft.business_id,
        vendor_id=draft.vendor_id,
        vendor_name=draft.vendor.name if draft.vendor else "Unknown Vendor",
        vendor_email=draft.vendor.email if draft.vendor else "",
        title=draft.title,
        amount=draft.amount,
        currency=draft.currency,
        category=draft.category,
        purpose=draft.purpose,
        invoice_number=draft.invoice_number,
        invoice_url=draft.invoice_url,
        description=draft.description,
        status=draft.status,
        cfo_recommendation=draft.cfo_recommendation,
        cfo_rationale=draft.cfo_rationale,
        budget_impact_pct=draft.budget_impact_pct,
        runway_impact_days=draft.runway_impact_days,
        details_hash=draft.details_hash,
        idempotency_key=draft.idempotency_key,
        approved_at=draft.approved_at,
        approved_by_id=draft.approved_by_id,
        approved_by_name=approved_by_name,
        expires_at=draft.expires_at,
        requires_dual_approval=draft.requires_dual_approval or False,
        secondary_approved_at=draft.secondary_approved_at,
        secondary_approved_by_id=draft.secondary_approved_by_id,
        secondary_approved_by_name=secondary_approved_by_name,
        rejection_reason=draft.rejection_reason,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        risk_assessment=risk_dict,
        policy_eligibility=policy_dict,
        approvals=approval_items,
    )


# ==============================================================================
# Vendor Management Endpoints
# ==============================================================================

@router.get("/vendors", response_model=List[VendorResponse])
def list_vendors(
    search: Optional[str] = Query(None, description="Optional search by vendor name"),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Lists registered suppliers and payees strictly scoped to current business tenant."""
    query = db.query(Vendor).filter(Vendor.business_id == business.id)
    if search:
        query = query.filter(Vendor.name.ilike(f"%{search}%"))
    return query.order_by(Vendor.name.asc()).all()


@router.post("/vendors", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor(
    request: VendorCreateRequest,
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Registers a new vendor payee with initial domain trust verification."""
    # Check if vendor already exists in this business
    existing = (
        db.query(Vendor)
        .filter(
            Vendor.business_id == business.id,
            (Vendor.name.ilike(request.name.strip())) | (Vendor.email == request.email.lower().strip()),
        )
        .first()
    )
    if existing:
        return existing

    # Compute initial trust score
    domain = request.email.split("@")[-1].lower() if "@" in request.email else ""
    if domain in GuardianRiskConfig.KNOWN_REPUTABLE_DOMAINS:
        initial_trust = 85.0
    elif domain in GuardianRiskConfig.FREE_EMAIL_PROVIDERS:
        initial_trust = 45.0
    else:
        initial_trust = 65.0

    vendor = Vendor(
        business_id=business.id,
        name=request.name.strip(),
        email=request.email.lower().strip(),
        website=request.website.strip() if request.website else None,
        bank_or_paypal_email=request.bank_or_paypal_email.lower().strip() if request.bank_or_paypal_email else None,
        status="ACTIVE",
        trust_score=initial_trust,
        total_paid=0.0,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    AuditService.log_event(
        db=db,
        business_id=business.id,
        user_id=current_user.id,
        stage="APPROVE",
        actor="SYSTEM",
        action="VENDOR_REGISTERED",
        summary=f"Registered payee vendor: {vendor.name} ({vendor.email})",
        details=f"Initial trust score: {initial_trust}/100. Disburse endpoint: {vendor.bank_or_paypal_email or vendor.email}",
        rationale="Vendor onboarded into business payee directory.",
    )

    return vendor


# ==============================================================================
# Payment Drafts Endpoints
# ==============================================================================

@router.post("/drafts", response_model=PaymentDraftResponse, status_code=status.HTTP_201_CREATED)
def create_payment_draft(
    request: PaymentDraftCreateRequest,
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a new payment draft with validation, idempotency checks, and optional Guardian risk scan."""
    # 1. Idempotency deduplication check
    if request.idempotency_key:
        existing = (
            db.query(PaymentDraft)
            .filter(
                PaymentDraft.business_id == business.id,
                PaymentDraft.idempotency_key == request.idempotency_key,
            )
            .first()
        )
        if existing:
            return format_draft_response(existing, db)

    # 2. Resolve vendor
    vendor: Optional[Vendor] = None
    if request.new_vendor:
        # Create inline vendor
        domain = request.new_vendor.email.split("@")[-1].lower() if "@" in request.new_vendor.email else ""
        initial_trust = 85.0 if domain in GuardianRiskConfig.KNOWN_REPUTABLE_DOMAINS else (
            45.0 if domain in GuardianRiskConfig.FREE_EMAIL_PROVIDERS else 65.0
        )
        vendor = Vendor(
            business_id=business.id,
            name=request.new_vendor.name.strip(),
            email=request.new_vendor.email.lower().strip(),
            website=request.new_vendor.website.strip() if request.new_vendor.website else None,
            bank_or_paypal_email=request.new_vendor.bank_or_paypal_email.lower().strip() if request.new_vendor.bank_or_paypal_email else None,
            status="ACTIVE",
            trust_score=initial_trust,
            total_paid=0.0,
        )
        db.add(vendor)
        db.flush()
    elif request.vendor_id:
        vendor = (
            db.query(Vendor)
            .filter(Vendor.id == request.vendor_id, Vendor.business_id == business.id)
            .first()
        )
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vendor #{request.vendor_id} does not exist in this business.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either vendor_id or new_vendor must be provided.",
        )

    # 3. Calculate financial runway and budget impact
    monthly_budget = business.monthly_budget if business.monthly_budget and business.monthly_budget > 0 else 50000.0
    burn_rate_daily = max(monthly_budget / 30.0, 1.0)
    budget_impact = round((request.amount / monthly_budget) * 100.0, 2)
    runway_days = int(request.amount / burn_rate_daily)

    # 4. Compute initial details_hash
    details_hash = compute_details_hash(
        vendor_id=vendor.id,
        amount=request.amount,
        currency=request.currency,
        purpose=request.purpose,
        invoice_number=request.invoice_number,
    )

    dual_threshold = business.settings.require_dual_approval_above if business.settings else 1000.0
    requires_dual = bool(request.amount >= dual_threshold)

    draft = PaymentDraft(
        business_id=business.id,
        vendor_id=vendor.id,
        created_by_id=current_user.id,
        title=request.title.strip(),
        amount=request.amount,
        currency=request.currency.upper(),
        category=request.category.strip(),
        purpose=request.purpose.strip(),
        invoice_number=request.invoice_number.strip() if request.invoice_number else None,
        invoice_url=request.invoice_url.strip() if request.invoice_url else None,
        description=f"Payment to {vendor.name}: {request.purpose}",
        status="DRAFT",
        requires_dual_approval=requires_dual,
        cfo_recommendation="REVIEW_REQUIRED" if budget_impact > 15.0 else "APPROVE",
        cfo_rationale=f"Impacts monthly budget by {budget_impact}%. Runway reduction estimate: ~{runway_days} day(s).",
        budget_impact_pct=budget_impact,
        runway_impact_days=runway_days,
        details_hash=details_hash,
        idempotency_key=request.idempotency_key,
        created_at=datetime.utcnow(),
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    # 5. Optional auto Guardian risk evaluation
    if request.auto_run_risk_scan:
        assessment = GuardianRiskEngine.evaluate(
            db=db,
            draft=draft,
            business=business,
            user_id=current_user.id,
            force_recalculate=True,
        )
        if assessment.risk_score >= 50.0 or assessment.verdict == "REQUIRES_DUAL_EXECUTIVE_APPROVAL":
            requires_dual = True
        draft.requires_dual_approval = requires_dual

        if assessment.verdict == "BLOCKED":
            draft.status = "REJECTED"
        elif assessment.verdict in ("REQUIRES_DUAL_EXECUTIVE_APPROVAL", "REQUIRES_MANUAL_REVIEW"):
            draft.status = "REVIEW_REQUIRED"
        else:
            # Safe to pay: marks draft as ready for user review & approval
            draft.status = "RISK_REVIEWED"
        db.commit()
        db.refresh(draft)

    AuditService.log_event(
        db=db,
        business_id=business.id,
        user_id=current_user.id,
        stage="DECIDE",
        actor="USER",
        action="CREATE_PAYMENT_DRAFT",
        summary=f"Drafted payment #{draft.id}: {draft.currency} {draft.amount:,.2f} to {vendor.name}",
        details=f"Status: {draft.status}. Purpose: {draft.purpose}. Hash: {details_hash[:12]}...",
        rationale="Payment proposal prepared for Guardian risk analysis and executive sign-off.",
    )

    return format_draft_response(draft, db)


@router.get("/drafts", response_model=List[PaymentDraftResponse])
def list_payment_drafts(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by payment status"),
    limit: int = Query(50, ge=1, le=100),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Lists payment drafts strictly scoped to current business with optional status filter."""
    query = db.query(PaymentDraft).filter(PaymentDraft.business_id == business.id)
    if status_filter:
        query = query.filter(PaymentDraft.status == status_filter.upper())

    drafts = query.order_by(PaymentDraft.created_at.desc()).limit(limit).all()
    return [format_draft_response(d, db) for d in drafts]


@router.get("/drafts/{draft_id}", response_model=PaymentDraftResponse)
def get_payment_draft(
    draft_id: int,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Retrieves full details and risk assessment for a specific payment draft."""
    draft = (
        db.query(PaymentDraft)
        .filter(PaymentDraft.id == draft_id, PaymentDraft.business_id == business.id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment draft #{draft_id} not found in this business account.",
        )
    return format_draft_response(draft, db)


@router.put("/drafts/{draft_id}", response_model=PaymentDraftResponse)
def update_payment_draft(
    draft_id: int,
    request: PaymentDraftUpdateRequest,
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates a payment draft. Invalides prior approval if commercial payment details change."""
    draft = (
        db.query(PaymentDraft)
        .filter(PaymentDraft.id == draft_id, PaymentDraft.business_id == business.id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment draft #{draft_id} not found in this business.",
        )

    if draft.status in ("COMPLETED", "PROVIDER_PENDING"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit draft #{draft_id} because it is already in '{draft.status}' state.",
        )

    # Track modifications
    modified_core = False
    if request.title is not None and request.title != draft.title:
        draft.title = request.title
    if request.amount is not None and request.amount != draft.amount:
        draft.amount = request.amount
        modified_core = True
    if request.currency is not None and request.currency != draft.currency:
        draft.currency = request.currency.upper()
        modified_core = True
    if request.category is not None:
        draft.category = request.category
    if request.purpose is not None and request.purpose != draft.purpose:
        draft.purpose = request.purpose
        modified_core = True
    if request.invoice_number is not None and request.invoice_number != draft.invoice_number:
        draft.invoice_number = request.invoice_number
        modified_core = True
    if request.invoice_url is not None:
        draft.invoice_url = request.invoice_url

    # Recompute cryptographic hash
    new_hash = compute_details_hash(
        vendor_id=draft.vendor_id,
        amount=draft.amount,
        currency=draft.currency,
        purpose=draft.purpose,
        invoice_number=draft.invoice_number,
    )

    # Invalidate approval if details changed
    if modified_core and (draft.status in ("APPROVED", "AWAITING_APPROVAL") or (draft.details_hash and new_hash != draft.details_hash)):
        prior_status = draft.status
        draft.details_hash = None
        draft.approved_at = None
        draft.approved_by_id = None
        draft.secondary_approved_at = None
        draft.secondary_approved_by_id = None
        draft.expires_at = None
        draft.status = "REVIEW_REQUIRED"

        AuditService.log_event(
            db=db,
            business_id=business.id,
            user_id=current_user.id,
            stage="DECIDE",
            actor="POLICY_ENGINE",
            action="APPROVAL_INVALIDATED",
            summary=f"Revoked prior approval for Draft #{draft.id} due to modified payment details",
            details=f"Previous status: {prior_status} -> Reset to REVIEW_REQUIRED. New fingerprint: {new_hash[:12]}...",
            rationale="Core payment parameters altered; security policy mandates fresh re-approval.",
        )

    draft.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(draft)

    return format_draft_response(draft, db)


@router.post("/drafts/{draft_id}/assess-risk", response_model=PaymentDraftResponse)
def assess_payment_draft_risk(
    draft_id: int,
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Executes the Guardian AI 10-signal risk evaluation on this draft."""
    draft = (
        db.query(PaymentDraft)
        .filter(PaymentDraft.id == draft_id, PaymentDraft.business_id == business.id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment draft #{draft_id} not found.",
        )

    if draft.status in ("COMPLETED", "PROVIDER_PENDING"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot re-scan draft #{draft_id} because payment is already '{draft.status}'.",
        )

    assessment = GuardianRiskEngine.evaluate(
        db=db,
        draft=draft,
        business=business,
        user_id=current_user.id,
        force_recalculate=True,
    )

    if assessment.verdict == "BLOCKED":
        draft.status = "REJECTED"
    elif assessment.verdict in ("REQUIRES_DUAL_EXECUTIVE_APPROVAL", "REQUIRES_MANUAL_REVIEW"):
        draft.status = "REVIEW_REQUIRED"
    else:
        draft.status = "RISK_REVIEWED"

    db.commit()
    db.refresh(draft)

    return format_draft_response(draft, db)


@router.post("/drafts/{draft_id}/approve", response_model=PaymentDraftResponse)
def approve_payment_draft(
    draft_id: int,
    request: PaymentDraftApproveRequest = PaymentDraftApproveRequest(),
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Explicitly approves a payment draft under policy engine rules."""
    draft = (
        db.query(PaymentDraft)
        .filter(PaymentDraft.id == draft_id, PaymentDraft.business_id == business.id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment draft #{draft_id} not found.",
        )

    draft = PaymentPolicyEngine.approve_draft(
        db=db,
        draft=draft,
        business=business,
        user=current_user,
        notes=request.notes,
        expected_details_hash=request.expected_details_hash,
        dual_approval_override=request.dual_approval_override,
    )

    return format_draft_response(draft, db)


@router.post("/drafts/{draft_id}/reject", response_model=PaymentDraftResponse)
def reject_payment_draft(
    draft_id: int,
    request: Optional[PaymentDraftRejectRequest] = None,
    notes: Optional[str] = Query(None, description="Optional rejection reason"),
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Explicitly rejects a payment draft and marks it as REJECTED."""
    draft = (
        db.query(PaymentDraft)
        .filter(PaymentDraft.id == draft_id, PaymentDraft.business_id == business.id)
        .first()
    )
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft #{draft_id} not found.")

    rejection_reason = None
    if request and request.reason:
        rejection_reason = request.reason
    elif notes:
        rejection_reason = notes

    draft = PaymentPolicyEngine.reject_draft(
        db=db,
        draft=draft,
        business=business,
        user=current_user,
        reason=rejection_reason,
    )

    return format_draft_response(draft, db)


# ==============================================================================
# Payment Decision Room Endpoints
# ==============================================================================

@router.get("/decision-room/{draft_id}", response_model=PaymentDecisionRoomResponse)
def get_payment_decision_room(
    draft_id: int,
    force_recalculate: bool = Query(False, description="Force deep re-scan of risk signals"),
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves comprehensive 6-section Payment Decision Room intelligence for a draft."""
    draft = (
        db.query(PaymentDraft)
        .filter(PaymentDraft.id == draft_id, PaymentDraft.business_id == business.id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment draft #{draft_id} not found in this business account.",
        )

    return DecisionRoomService.get_decision_room_data(
        db=db,
        draft=draft,
        business=business,
        user=current_user,
        force_recalculate_risk=force_recalculate,
    )


@router.post("/decision-room/demo-scenario/{scenario_key}", response_model=PaymentDecisionRoomResponse)
def load_decision_room_demo_scenario(
    scenario_key: str,
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Loads or creates reproducible Hackathon demonstration scenarios (normal or suspicious)."""
    try:
        draft = DecisionRoomService.ensure_demo_scenario(
            db=db,
            business=business,
            user=current_user,
            scenario_key=scenario_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return DecisionRoomService.get_decision_room_data(
        db=db,
        draft=draft,
        business=business,
        user=current_user,
        force_recalculate_risk=False,
    )


@router.post("/drafts/{draft_id}/hold", response_model=PaymentDraftResponse)
def hold_payment_draft(
    draft_id: int,
    request: PaymentDraftHoldRequest = PaymentDraftHoldRequest(),
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Holds/pauses a payment draft for executive review (status -> REVIEW_REQUIRED)."""
    draft = (
        db.query(PaymentDraft)
        .filter(PaymentDraft.id == draft_id, PaymentDraft.business_id == business.id)
        .first()
    )
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft #{draft_id} not found.")

    if draft.status in ("COMPLETED", "PROVIDER_PENDING"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot hold a draft in terminal/in-flight status '{draft.status}'.",
        )

    previous_status = draft.status
    draft.status = "REVIEW_REQUIRED"
    draft.details_hash = None

    AuditService.log_event(
        db=db,
        business_id=business.id,
        user_id=current_user.id,
        stage="APPROVE",
        actor="USER",
        action="HOLD_PAYMENT_REQUESTED",
        summary=f"Payment draft #{draft.id} put on hold by {current_user.full_name}",
        details=f"Previous status: {previous_status}. Notes: {request.notes or 'Executive hold requested.'}",
        rationale="Disbursement paused pending further verification and security clearance.",
        decision_id=draft.id,
    )
    db.commit()
    db.refresh(draft)

    return format_draft_response(draft, db)


@router.post("/drafts/{draft_id}/request-review", response_model=PaymentDraftResponse)
def request_draft_review(
    draft_id: int,
    request: PaymentDraftReviewRequest = PaymentDraftReviewRequest(),
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Flags a payment draft for human executive review."""
    draft = (
        db.query(PaymentDraft)
        .filter(PaymentDraft.id == draft_id, PaymentDraft.business_id == business.id)
        .first()
    )
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft #{draft_id} not found.")

    previous_status = draft.status
    draft.status = "AWAITING_APPROVAL"

    AuditService.log_event(
        db=db,
        business_id=business.id,
        user_id=current_user.id,
        stage="APPROVE",
        actor="USER",
        action="HUMAN_REVIEW_REQUESTED",
        summary=f"Human review requested for Draft #{draft.id} by {current_user.full_name}",
        details=f"Prior status: {previous_status}. Notes: {request.notes or 'Executive review requested.'}",
        rationale="Disbursement flagged for multi-party review.",
        decision_id=draft.id,
    )
    db.commit()
    db.refresh(draft)

    return format_draft_response(draft, db)


# ==============================================================================
# Payment Execution & Settlement
# ==============================================================================

@router.post("/execute", response_model=ExecutePaymentResponse)
async def execute_payment(
    request: ExecutePaymentRequest,
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Executes an APPROVED payment draft via Simulated Clearing Provider or PayPal Sandbox.
    
    Security Checks:
    1. Draft must be in 'APPROVED' status.
    2. Details hash must match current draft fields (tamper verification).
    3. Idempotency key avoids double debits.
    4. State transitions: APPROVED -> PROVIDER_PENDING -> COMPLETED upon confirmation.
    """
    draft = (
        db.query(PaymentDraft)
        .filter(PaymentDraft.id == request.draft_id, PaymentDraft.business_id == business.id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment draft #{request.draft_id} not found.",
        )

    # 1. Idempotency check: Already completed or existing execution with this key
    if draft.status == "COMPLETED":
        tx = (
            db.query(Transaction)
            .filter(Transaction.payment_draft_id == draft.id, Transaction.business_id == business.id)
            .first()
        )
        return ExecutePaymentResponse(
            transaction_id=tx.id if tx else 0,
            draft_id=draft.id,
            status="COMPLETED",
            amount=draft.amount,
            currency=draft.currency,
            recipient_email=draft.vendor.email if draft.vendor else "",
            provider_reference=tx.paypal_order_id if tx else "SETTLED",
            payment_method=tx.payment_method if tx else "SIMULATED_PROVIDER",
            is_sandbox=tx.is_sandbox if tx else True,
            settled_at=tx.settled_at if tx else draft.updated_at,
            message="Payment was already completed (Idempotent response).",
        )

    if request.idempotency_key:
        existing_tx = (
            db.query(Transaction)
            .filter(
                Transaction.business_id == business.id,
                Transaction.idempotency_key == request.idempotency_key,
            )
            .first()
        )
        if existing_tx and existing_tx.status == "COMPLETED":
            return ExecutePaymentResponse(
                transaction_id=existing_tx.id,
                draft_id=draft.id,
                status=existing_tx.status,
                amount=existing_tx.amount,
                currency=existing_tx.currency,
                recipient_email=draft.vendor.email if draft.vendor else "",
                provider_reference=existing_tx.paypal_order_id or "SETTLED",
                payment_method=existing_tx.payment_method,
                is_sandbox=existing_tx.is_sandbox,
                settled_at=existing_tx.settled_at,
                message="Payment already executed with this idempotency key.",
            )

    # 2. Strict Policy Clearance Check (Expiration, Approved status, Tamper Fingerprint, Guardian Risk, Dual Approval)
    PaymentPolicyEngine.verify_execution_clearance(db=db, draft=draft, business=business)

    vendor = db.query(Vendor).filter(Vendor.id == draft.vendor_id).first()
    recipient_email = vendor.bank_or_paypal_email or (vendor.email if vendor else "payee@example.com")

    # ==========================================================================
    # BRANCH 1: SIMULATED_PROVIDER (Guaranteed local sandbox & demonstration)
    # ==========================================================================
    if request.payment_method == "SIMULATED_PROVIDER":
        # Transition draft to PROVIDER_PENDING
        draft.status = "PROVIDER_PENDING"
        db.commit()

        provider_ref = f"SIM-TXN-{uuid.uuid4().hex[:12].upper()}"
        capture_ref = f"SIM-CAP-{uuid.uuid4().hex[:10].upper()}"

        transaction = Transaction(
            business_id=business.id,
            vendor_id=draft.vendor_id,
            payment_draft_id=draft.id,
            transaction_type="EXPENSE",
            amount=draft.amount,
            currency=draft.currency,
            status="PROVIDER_PENDING",
            category=draft.category,
            description=f"Payment for {draft.title} (Purpose: {draft.purpose})",
            paypal_order_id=provider_ref,
            paypal_capture_id=capture_ref,
            payment_method="SIMULATED_PROVIDER",
            idempotency_key=request.idempotency_key,
            is_sandbox=True,
            raw_paypal_response=json.dumps({"provider": "SIMULATED_CLEARING_HOUSE", "settlement": "INSTANT"}),
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        # Provider confirms settlement
        settled_at = datetime.utcnow()
        transaction.status = "COMPLETED"
        transaction.settled_at = settled_at
        draft.status = "COMPLETED"

        # Update business treasury ledger
        business.total_balance -= draft.amount
        business.monthly_spent += draft.amount

        # Update vendor total paid
        if vendor:
            vendor.total_paid += draft.amount

        # Audit logs: PAY & MONITOR stages
        AuditService.log_event(
            db=db,
            business_id=business.id,
            user_id=current_user.id,
            stage="PAY",
            actor="PAYMENT_AGENT",
            action="DISPATCH_PAYMENT_ORDER",
            summary=f"Dispatched payment order of {draft.currency} {draft.amount:,.2f} to {vendor.name if vendor else 'Vendor'}",
            details=f"Provider reference: {provider_ref}. Recipient: {recipient_email}. Method: SIMULATED_PROVIDER",
            rationale="Executed approved payment draft through clearing provider.",
        )
        AuditService.log_event(
            db=db,
            business_id=business.id,
            user_id=current_user.id,
            stage="MONITOR",
            actor="SYSTEM",
            action="SETTLEMENT_CONFIRMED",
            summary=f"Clearing provider confirmed settlement for Transaction #{transaction.id}",
            details=f"Capture ref: {capture_ref}. Debited {draft.currency} {draft.amount:,.2f} from corporate balance.",
            rationale="Provider confirmed fund settlement. Treasury ledger balances decremented.",
        )

        db.commit()
        db.refresh(transaction)

        return ExecutePaymentResponse(
            transaction_id=transaction.id,
            draft_id=draft.id,
            status="COMPLETED",
            amount=transaction.amount,
            currency=transaction.currency,
            recipient_email=recipient_email,
            provider_reference=provider_ref,
            payment_method="SIMULATED_PROVIDER",
            is_sandbox=True,
            settled_at=settled_at,
            message="Payment executed and settlement confirmed by Clearing Provider. Treasury ledger updated.",
        )

    # ==========================================================================
    # BRANCH 2: PAYPAL_SANDBOX
    # ==========================================================================
    elif request.payment_method == "PAYPAL_SANDBOX":
        try:
            tx, order_info = await PayPalService.create_order_for_draft(
                db=db,
                draft=draft,
                business=business,
                user=current_user,
                idempotency_key=request.idempotency_key,
            )
            return ExecutePaymentResponse(
                transaction_id=tx.id,
                draft_id=draft.id,
                status="PROVIDER_PENDING",
                amount=tx.amount,
                currency=tx.currency,
                recipient_email=order_info["recipient_email"],
                provider_reference=order_info["paypal_order_id"],
                payment_method="PAYPAL_SANDBOX",
                is_sandbox=tx.is_sandbox,
                approval_url=order_info.get("approval_url"),
                settled_at=None,
                message=f"PayPal Order {order_info['paypal_order_id']} created. Awaiting buyer sandbox authorization.",
            )
        except PayPalConfigurationError as exc:
            draft.status = "APPROVED"
            db.commit()
            raise HTTPException(status_code=400, detail={"error": "paypal_not_configured", "message": str(exc)})
        except PayPalAPIError as exc:
            draft.status = "FAILED"
            db.commit()
            raise HTTPException(status_code=502, detail={"error": "paypal_api_error", "message": str(exc)})
        except ValueError as exc:
            draft.status = "APPROVED"
            db.commit()
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            draft.status = "FAILED"
            db.commit()
            raise HTTPException(status_code=500, detail=f"Unexpected payment failure: {str(exc)}")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported payment method '{request.payment_method}'. Use 'SIMULATED_PROVIDER' or 'PAYPAL_SANDBOX'.",
        )


# ==============================================================================
# PayPal Dedicated Management Endpoints (Orders v2 & Sandbox)
# ==============================================================================

@router.get("/paypal/config", response_model=PayPalConfigResponse)
async def get_paypal_configuration():
    """Returns PayPal REST API configuration status and operating mode without exposing secrets."""
    status_info = await PayPalService.verify_credentials()
    return PayPalConfigResponse(
        configured=status_info["configured"],
        mode=status_info["mode"],
        base_url=status_info["base_url"],
        client_id_preview=status_info.get("client_id_preview"),
        status=status_info["status"],
        details=status_info["details"],
    )


@router.post("/paypal/orders", response_model=PayPalOrderDraftResponse)
async def create_paypal_order_for_draft(
    request: PayPalCreateOrderDraftRequest,
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates an authentic PayPal Orders v2 checkout session for an APPROVED payment draft."""
    draft = (
        db.query(PaymentDraft)
        .filter(PaymentDraft.id == request.draft_id, PaymentDraft.business_id == business.id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment draft #{request.draft_id} not found in this business account.",
        )

    try:
        transaction, order_info = await PayPalService.create_order_for_draft(
            db=db,
            draft=draft,
            business=business,
            user=current_user,
            return_url=request.return_url,
            cancel_url=request.cancel_url,
            idempotency_key=request.idempotency_key,
        )

        return PayPalOrderDraftResponse(
            transaction_id=transaction.id,
            draft_id=draft.id,
            paypal_order_id=order_info["paypal_order_id"],
            status=order_info["status"],
            is_sandbox=transaction.is_sandbox,
            approval_url=order_info.get("approval_url"),
            amount=transaction.amount,
            currency=transaction.currency,
            recipient_email=order_info["recipient_email"],
        )
    except PayPalConfigurationError as exc:
        raise HTTPException(status_code=400, detail={"error": "paypal_not_configured", "message": str(exc)})
    except PayPalAPIError as exc:
        raise HTTPException(status_code=502, detail={"error": "paypal_api_error", "message": str(exc)})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected order creation failure: {str(exc)}")


@router.get("/paypal/orders/{order_id}")
async def get_paypal_order_details(
    order_id: str,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Queries live order state from PayPal REST API."""
    try:
        return await PayPalService.get_order_details(order_id)
    except PayPalConfigurationError as exc:
        raise HTTPException(status_code=400, detail={"error": "paypal_not_configured", "message": str(exc)})
    except PayPalAPIError as exc:
        raise HTTPException(status_code=502, detail={"error": "paypal_api_error", "message": str(exc)})


@router.post("/paypal/orders/{order_id}/capture", response_model=PaymentCaptureResponse)
async def capture_paypal_order_by_id(
    order_id: str,
    transaction_id: Optional[int] = Query(None, description="Optional transaction ID"),
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Captures an approved PayPal order on the backend and updates treasury balances upon confirmation."""
    query = db.query(Transaction).filter(Transaction.business_id == business.id)
    if transaction_id:
        query = query.filter(Transaction.id == transaction_id)
    else:
        query = query.filter(Transaction.paypal_order_id == order_id)
    transaction = query.first()

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction with PayPal Order ID '{order_id}' not found in this business.",
        )

    try:
        tx, capture_res = await PayPalService.capture_order(
            db=db,
            transaction_id=transaction.id,
            paypal_order_id=order_id,
            business=business,
            user=current_user,
        )
        return PaymentCaptureResponse(
            transaction_id=tx.id,
            paypal_order_id=order_id,
            paypal_capture_id=tx.paypal_capture_id,
            status=tx.status,
            is_sandbox=tx.is_sandbox,
            amount=tx.amount,
            currency=tx.currency,
            details=capture_res.get("details"),
        )
    except PayPalConfigurationError as exc:
        raise HTTPException(status_code=400, detail={"error": "paypal_not_configured", "message": str(exc)})
    except PayPalAPIError as exc:
        raise HTTPException(status_code=502, detail={"error": "paypal_api_error", "message": str(exc)})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Capture failure: {str(exc)}")


@router.post("/paypal/orders/{transaction_id}/cancel")
def cancel_paypal_order(
    transaction_id: int,
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancels a pending PayPal order session and re-enables the draft for approval."""
    try:
        tx = PayPalService.cancel_order(
            db=db,
            transaction_id=transaction_id,
            business=business,
            user=current_user,
        )
        return {"status": "CANCELLED", "transaction_id": tx.id, "message": "PayPal order cancelled."}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ==============================================================================
# Legacy PayPal Routes (Maintained for Backwards Compatibility)
# ==============================================================================

@router.post("/create-order", response_model=PayPalOrderResponse)
async def create_payment_order(
    request: CreatePaymentOrderRequest,
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a real PayPal REST API checkout order strictly scoped to caller's business."""
    draft = (
        db.query(PaymentDraft)
        .filter(PaymentDraft.id == request.decision_id, PaymentDraft.business_id == business.id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment draft #{request.decision_id} not found in this business account.",
        )

    risk = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.payment_draft_id == draft.id, RiskAssessment.business_id == business.id)
        .first()
    )
    if risk and risk.verdict == "BLOCKED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment blocked: Guardian AI flagged this transaction as high risk / fraud.",
        )

    vendor = db.query(Vendor).filter(Vendor.id == draft.vendor_id).first()
    recipient_email = vendor.email if vendor else "payee@example.com"

    try:
        access_token = await PayPalService.get_access_token()
        url = f"{settings.paypal_base_url}/v2/checkout/orders"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        order_payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": f"DRAFT_{draft.id}_BIZ_{business.id}",
                    "description": f"Guardian CFO: {draft.title}",
                    "amount": {
                        "currency_code": draft.currency,
                        "value": f"{draft.amount:.2f}",
                    },
                    "payee": {
                        "email_address": recipient_email,
                    },
                }
            ],
            "application_context": {
                "brand_name": f"Guardian CFO ({business.name})",
                "landing_page": "BILLING",
                "user_action": "PAY_NOW",
                "return_url": request.return_url or "http://localhost:3000/dashboard/payments/success",
                "cancel_url": request.cancel_url or "http://localhost:3000/dashboard/payments/cancel",
            },
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, headers=headers, json=order_payload)
            if resp.status_code not in (200, 201):
                raise PayPalAPIError(f"PayPal create order rejected: {resp.text}")
            result = resp.json()

        paypal_order_id = result.get("id")
        links = result.get("links", [])
        approve_url = next((l["href"] for l in links if l.get("rel") == "approve"), None)

        transaction = Transaction(
            business_id=business.id,
            vendor_id=draft.vendor_id,
            payment_draft_id=draft.id,
            amount=draft.amount,
            currency=draft.currency,
            status="APPROVED",
            category=draft.category,
            paypal_order_id=paypal_order_id,
            is_sandbox=(settings.PAYPAL_MODE.lower() == "sandbox"),
            raw_paypal_response=resp.text,
        )
        db.add(transaction)
        draft.status = "APPROVED"
        db.commit()
        db.refresh(transaction)

        AuditService.log_event(
            db=db,
            business_id=business.id,
            user_id=current_user.id,
            stage="PAY",
            actor="PAYMENT_AGENT",
            action="CREATE_PAYPAL_ORDER",
            summary=f"Created PayPal Order {paypal_order_id} in {settings.PAYPAL_MODE.upper()} mode",
            details=f"Transaction #{transaction.id}",
            rationale="Dispatched official PayPal v2 checkout order.",
        )

        return PayPalOrderResponse(
            transaction_id=transaction.id,
            decision_id=draft.id,
            paypal_order_id=paypal_order_id,
            status=result.get("status", "CREATED"),
            is_sandbox=transaction.is_sandbox,
            approval_url=approve_url,
            amount=transaction.amount,
            currency=transaction.currency,
            recipient_email=recipient_email,
        )
    except PayPalConfigurationError as exc:
        raise HTTPException(status_code=400, detail={"error": "paypal_not_configured", "message": str(exc)})
    except PayPalAPIError as exc:
        raise HTTPException(status_code=502, detail={"error": "paypal_api_error", "message": str(exc)})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected payment failure: {str(exc)}")


@router.post("/capture-order", response_model=PaymentCaptureResponse)
async def capture_payment_order(
    request: CapturePaymentOrderRequest,
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Captures an approved PayPal order strictly scoped to caller's business."""
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == request.transaction_id, Transaction.business_id == business.id)
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction #{request.transaction_id} not found in this business.")

    try:
        tx, capture_res = await PayPalService.capture_order(
            db=db,
            transaction_id=transaction.id,
            paypal_order_id=request.paypal_order_id,
            business=business,
            user=current_user,
        )
        return PaymentCaptureResponse(
            transaction_id=tx.id,
            paypal_order_id=request.paypal_order_id,
            paypal_capture_id=tx.paypal_capture_id,
            status=tx.status,
            is_sandbox=tx.is_sandbox,
            amount=tx.amount,
            currency=tx.currency,
            details=capture_res.get("details"),
        )
    except PayPalConfigurationError as exc:
        raise HTTPException(status_code=400, detail={"error": "paypal_not_configured", "message": str(exc)})
    except PayPalAPIError as exc:
        raise HTTPException(status_code=502, detail={"error": "paypal_api_error", "message": str(exc)})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Capture failure: {str(exc)}")


@router.get("/transactions", response_model=List[TransactionItemResponse])
def list_transactions(
    limit: int = Query(50, ge=1, le=100),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Lists payment transactions strictly scoped to authenticated business tenant."""
    txs = (
        db.query(Transaction)
        .filter(Transaction.business_id == business.id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .all()
    )
    return txs
