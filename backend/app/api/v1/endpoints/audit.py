"""Audit and Explainability Endpoints - Multi-Tenant Scoped
"""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_business
from app.core.config import settings
from app.models.business import Business
from app.models.vendor import Vendor
from app.models.payment import PaymentDraft, PaymentApproval, Transaction
from app.models.guardian import RiskAssessment
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import (
    AuditLogItem,
    ExplainabilityReport,
    ApprovalDetails,
    ApproverDetail,
    RejectionDetail,
    ProviderStatusDetails,
)

router = APIRouter()


@router.get("/logs", response_model=List[AuditLogItem])
def get_audit_logs(
    search: Optional[str] = Query(None, description="Search keyword in summary, action, or details"),
    stage: Optional[str] = Query(None, description="Filter by pipeline stage (e.g. UNDERSTAND, ANALYZE, INVESTIGATE, DECIDE, APPROVE, PAY, MONITOR, EXPLAIN)"),
    actor: Optional[str] = Query(None, description="Filter by actor (e.g. AI_CFO, GUARDIAN_AI, PAYMENT_AGENT, USER, SYSTEM)"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    decision_id: Optional[int] = Query(None, description="Filter by decision ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Retrieves immutable audit logs strictly scoped to authenticated business tenant with search and filters."""
    query = db.query(AuditLog).filter(AuditLog.business_id == business.id)

    if decision_id is not None:
        query = query.filter(AuditLog.decision_id == decision_id)

    if stage:
        query = query.filter(AuditLog.stage == stage.upper())

    if actor:
        query = query.filter(AuditLog.actor == actor.upper())

    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (AuditLog.summary.ilike(search_pattern)) |
            (AuditLog.action.ilike(search_pattern)) |
            (AuditLog.details.ilike(search_pattern)) |
            (AuditLog.rationale.ilike(search_pattern))
        )

    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    return [
        AuditLogItem(
            id=log.id,
            decision_id=log.decision_id,
            stage=log.stage,
            actor=log.actor,
            action=log.action,
            summary=log.summary,
            details=log.details,
            rationale=log.rationale,
            ip_address=log.ip_address,
            timestamp=log.created_at,
        )
        for log in logs
    ]


@router.get("/explain/{decision_id}", response_model=ExplainabilityReport)
def explain_decision(
    decision_id: int,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Provides a full transparent 6-Question Explainability report for a payment decision.
    
    Dimensions:
    1. What happened?
    2. Why was it flagged?
    3. What evidence was detected?
    4. What action was taken?
    5. Who approved or rejected it?
    6. What is the final provider status?
    """
    draft = (
        db.query(PaymentDraft)
        .filter(PaymentDraft.id == decision_id, PaymentDraft.business_id == business.id)
        .first()
    )
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision #{decision_id} not found in this business account.",
        )

    vendor = db.query(Vendor).filter(Vendor.id == draft.vendor_id).first() if draft.vendor_id else None
    vendor_name = vendor.name if vendor else "Vendor"

    risk = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.payment_draft_id == draft.id, RiskAssessment.business_id == business.id)
        .order_by(RiskAssessment.created_at.desc())
        .first()
    )

    approvals = (
        db.query(PaymentApproval)
        .filter(PaymentApproval.payment_draft_id == draft.id)
        .order_by(PaymentApproval.approved_at.asc())
        .all()
    )

    tx = (
        db.query(Transaction)
        .filter(Transaction.payment_draft_id == draft.id, Transaction.business_id == business.id)
        .first()
    )

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.business_id == business.id, AuditLog.decision_id == draft.id)
        .order_by(AuditLog.created_at.asc())
        .all()
    )
    if not logs:
        # Fallback to recent tenant logs
        logs = (
            db.query(AuditLog)
            .filter(AuditLog.business_id == business.id)
            .order_by(AuditLog.created_at.desc())
            .limit(10)
            .all()
        )

    # 1. WHAT HAPPENED?
    what_happened = (
        f"Payment Draft #{draft.id} for {draft.currency} {draft.amount:,.2f} titled '{draft.title}' was initiated for payee '{vendor_name}'. "
        f"Guardian AI evaluated the security and fraud risk profile (Current Status: {draft.status}). "
        f"Purpose: {draft.purpose or 'General business disbursement'}. Invoice Ref: {draft.invoice_number or 'None'}."
    )

    # 2. WHY WAS IT FLAGGED?
    if risk:
        if risk.risk_score >= 75:
            flag_summary = f"Hard-flagged as CRITICAL RISK ({risk.risk_score:.0f}/100) due to severe risk indicators. {risk.plain_explanation or ''}"
        elif risk.risk_score >= 50:
            flag_summary = f"Flagged as HIGH RISK ({risk.risk_score:.0f}/100) requiring mandatory multi-party executive sign-off. {risk.plain_explanation or ''}"
        elif risk.risk_score >= 25:
            flag_summary = f"Flagged as MEDIUM RISK ({risk.risk_score:.0f}/100). Standard executive review recommended. {risk.plain_explanation or ''}"
        else:
            flag_summary = f"Assessed as LOW RISK ({risk.risk_score:.0f}/100). Payment passed automated security heuristics."
    else:
        flag_summary = "No security scan performed yet."

    # 3. WHAT EVIDENCE WAS DETECTED?
    evidence_detected: List[str] = []
    if risk:
        if risk.supporting_evidence:
            try:
                ev = json.loads(risk.supporting_evidence)
                if isinstance(ev, list):
                    evidence_detected.extend([str(item) for item in ev])
                else:
                    evidence_detected.append(str(ev))
            except Exception:
                evidence_detected.append(risk.supporting_evidence)

        if risk.flags:
            try:
                fl = json.loads(risk.flags)
                if isinstance(fl, list):
                    for item in fl:
                        evidence_detected.append(f"Flag: {item}")
            except Exception:
                pass

        if not risk.vendor_verified:
            evidence_detected.append(f"Vendor '{vendor_name}' is not yet verified or has no verified history.")
        if risk.is_duplicate_invoice:
            evidence_detected.append(f"Duplicate invoice reference '{draft.invoice_number}' detected.")
        if not evidence_detected:
            evidence_detected.append(f"Verdict: {risk.verdict}. Heuristic risk score calculated at {risk.risk_score:.0f}/100.")
    else:
        evidence_detected.append("Pre-flight investigation pending.")

    # 4. WHAT ACTION WAS TAKEN?
    if draft.status == "REJECTED":
        action_taken = f"Disbursement Rejected: Officer declined payment. Reason: {draft.rejection_reason or 'Policy non-compliance'}"
    elif draft.status == "COMPLETED":
        action_taken = "Payment Executed & Settled: Approved by officers and confirmed settled by PayPal REST API."
    elif draft.status == "APPROVED":
        action_taken = "Payment Cleared for Payout: All policy and approval gates satisfied; awaiting disbursement."
    elif draft.requires_dual_approval:
        action_taken = "Policy Guardrail: Dual executive authorization mandated before PayPal checkout allowed."
    elif risk and risk.risk_score >= 75:
        action_taken = "Policy Guardrail: Payment hard-blocked from automated execution due to Critical Risk threshold."
    else:
        action_taken = "Standard Policy: Payment requires single executive sign-off."

    # 5. WHO APPROVED OR REJECTED IT?
    approver_details_list: List[ApproverDetail] = []
    for idx, ap in enumerate(approvals, start=1):
        if ap.status != "APPROVED":
            continue
        step = 2 if ap.approval_role == "SECONDARY_APPROVER" else idx
        ap_user = db.query(User).filter(User.id == ap.approved_by_id).first() if ap.approved_by_id else None
        approver_details_list.append(
            ApproverDetail(
                step=step,
                user_id=ap.approved_by_id,
                name=ap_user.full_name if ap_user else f"Signer #{ap.approved_by_id or step}",
                email=ap_user.email if ap_user else None,
                role=ap_user.role if ap_user else ap.approval_role,
                approved_at=ap.approved_at,
                notes=ap.notes,
            )
        )

    rejection_detail = None
    if draft.status == "REJECTED":
        rej_user = db.query(User).filter(User.id == draft.approved_by_id).first() if draft.approved_by_id else None
        rejection_detail = RejectionDetail(
            user_id=draft.approved_by_id,
            name=rej_user.full_name if rej_user else "Reviewing Officer",
            email=rej_user.email if rej_user else None,
            rejected_at=draft.approved_at or draft.updated_at,
            reason=draft.rejection_reason or "Disbursement rejected by executive officer.",
        )

    approval_structure = ApprovalDetails(
        status=draft.status,
        requires_dual_approval=draft.requires_dual_approval,
        approvers=approver_details_list,
        rejected_by=rejection_detail,
    )

    # 6. WHAT IS THE FINAL PROVIDER STATUS?
    provider_status = ProviderStatusDetails(
        provider="PayPal REST API",
        mode=settings.PAYPAL_MODE,
        order_id=tx.paypal_order_id if tx else None,
        capture_id=tx.paypal_capture_id if tx else None,
        status=draft.status if draft.status in ("COMPLETED", "FAILED", "PROVIDER_PENDING") else (
            "CAPTURED" if tx and tx.status == "COMPLETED" else "NOT_INITIATED"
        ),
        reconciled_at=tx.created_at if tx else None,
        settlement_amount=f"{draft.currency} {draft.amount:,.2f}" if draft.status == "COMPLETED" else None,
    )

    guardian_summary = (
        f"Verdict: {risk.verdict} | Risk Score: {risk.risk_score:.0f}/100 ({risk.risk_level}) | "
        f"Vendor Verified: {risk.vendor_verified}"
        if risk
        else "No security scan performed yet."
    )

    return ExplainabilityReport(
        decision_id=draft.id,
        title=draft.title,
        vendor=vendor_name,
        amount=draft.amount,
        currency=draft.currency,
        current_status=draft.status,
        cfo_reasoning=draft.cfo_rationale or "Reviewed against budget and cashflow projections.",
        guardian_security_summary=guardian_summary,
        audit_trail=[
            AuditLogItem(
                id=log.id,
                decision_id=draft.id,
                stage=log.stage,
                actor=log.actor,
                action=log.action,
                summary=log.summary,
                details=log.details,
                rationale=log.rationale,
                ip_address=log.ip_address,
                timestamp=log.created_at,
            )
            for log in logs
        ],
        what_happened=what_happened,
        why_flagged=flag_summary,
        evidence_detected=evidence_detected,
        action_taken=action_taken,
        approval_details=approval_structure,
        final_provider_status=provider_status,
    )
