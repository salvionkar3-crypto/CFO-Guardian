"""Guardian AI Fraud and Risk Endpoints - Multi-Tenant Scoped

Provides:
- Deterministic 10-signal risk investigation
- Detailed evidence, signals breakdown, and missing info
- Configurable risk policy thresholds
- Security alert monitoring and resolution
"""

import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_business, get_current_user
from app.models.user import User
from app.models.business import Business
from app.models.payment import PaymentDraft
from app.models.guardian import RiskAssessment, SecurityAlert
from app.schemas.guardian import (
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    RiskPolicyThresholds,
    RiskSignalItem,
    SecurityAlertResponse,
)
from app.services.guardian_service import GuardianRiskEngine, GuardianRiskConfig
from app.core.logging_config import logger

router = APIRouter()


def _format_assessment_response(assessment: RiskAssessment) -> RiskAssessmentResponse:
    """Helper to deserialize JSON text fields into typed schema contracts."""
    signals_raw = json.loads(assessment.risk_signals) if assessment.risk_signals else []
    evidence_raw = json.loads(assessment.supporting_evidence) if assessment.supporting_evidence else []
    missing_raw = json.loads(assessment.missing_information) if assessment.missing_information else []
    flags_raw = json.loads(assessment.flags) if assessment.flags else []

    detected_signals = [RiskSignalItem(**s) for s in signals_raw]

    return RiskAssessmentResponse(
        id=assessment.id,
        decision_id=assessment.payment_draft_id or 0,
        risk_score=assessment.risk_score,
        risk_level=assessment.risk_level,
        verdict=assessment.verdict,
        recommended_action=assessment.recommended_action or "MANUAL_REVIEW_REQUIRED",
        plain_explanation=assessment.plain_explanation or (
            f"Risk score evaluated at {assessment.risk_score}/100 ({assessment.risk_level})."
        ),
        detected_signals=detected_signals,
        supporting_evidence=evidence_raw,
        missing_information=missing_raw,
        flags=flags_raw,
        vendor_verified=assessment.vendor_verified,
        is_duplicate_invoice=assessment.is_duplicate_invoice,
        anomaly_detected=assessment.anomaly_detected,
        verification_hash=assessment.verification_hash,
        created_at=assessment.created_at.isoformat() if assessment.created_at else None,
    )


@router.post("/assess-risk", response_model=RiskAssessmentResponse)
@router.post("/decide", response_model=RiskAssessmentResponse)
def assess_risk(
    request: RiskAssessmentRequest,
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Triggers Guardian AI 10-signal fraud and risk scan strictly scoped to caller's business."""
    # Tenant verification: Draft must belong to caller's business
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

    assessment = GuardianRiskEngine.evaluate(
        db=db,
        draft=draft,
        business=business,
        user_id=current_user.id,
        force_recalculate=request.force_deep_scan,
    )

    return _format_assessment_response(assessment)


@router.get("/policy", response_model=RiskPolicyThresholds)
def get_risk_policy():
    """Returns the active configurable demonstration risk thresholds and policy guidelines."""
    return RiskPolicyThresholds(
        low_min=0.0,
        low_max=GuardianRiskConfig.THRESHOLD_LOW_MAX,
        medium_min=GuardianRiskConfig.THRESHOLD_LOW_MAX + 1.0,
        medium_max=GuardianRiskConfig.THRESHOLD_MEDIUM_MAX,
        high_min=GuardianRiskConfig.THRESHOLD_MEDIUM_MAX + 1.0,
        high_max=GuardianRiskConfig.THRESHOLD_HIGH_MAX,
        critical_min=GuardianRiskConfig.THRESHOLD_CRITICAL_MIN,
        critical_max=100.0,
        notice="Initial configurable demonstration thresholds, not validated fraud probabilities.",
    )


@router.get("/assessments", response_model=List[RiskAssessmentResponse])
def list_assessments(
    limit: int = Query(25, ge=1, le=100),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Lists recent risk evaluations scoped to authenticated business tenant."""
    assessments = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.business_id == business.id)
        .order_by(RiskAssessment.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_format_assessment_response(a) for a in assessments]


@router.get("/assessments/{decision_id}", response_model=RiskAssessmentResponse)
def get_assessment_for_decision(
    decision_id: int,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Retrieves specific risk evaluation by payment draft decision ID."""
    assessment = (
        db.query(RiskAssessment)
        .filter(
            RiskAssessment.payment_draft_id == decision_id,
            RiskAssessment.business_id == business.id,
        )
        .first()
    )
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No risk assessment found for decision #{decision_id}.",
        )
    return _format_assessment_response(assessment)


@router.get("/alerts", response_model=List[SecurityAlertResponse])
def list_security_alerts(
    status_filter: Optional[str] = Query(None, description="OPEN, RESOLVED, DISMISSED"),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Lists security alerts strictly scoped to authenticated business tenant."""
    query = db.query(SecurityAlert).filter(SecurityAlert.business_id == business.id)
    if status_filter:
        query = query.filter(SecurityAlert.status == status_filter.upper())
    alerts = query.order_by(SecurityAlert.created_at.desc()).all()
    return alerts


@router.post("/alerts/{alert_id}/resolve", response_model=SecurityAlertResponse)
def resolve_security_alert(
    alert_id: int,
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resolves an open security alert."""
    alert = (
        db.query(SecurityAlert)
        .filter(SecurityAlert.id == alert_id, SecurityAlert.business_id == business.id)
        .first()
    )
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security alert #{alert_id} not found.",
        )
    alert.status = "RESOLVED"
    alert.resolved_by_id = current_user.id
    alert.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return alert
