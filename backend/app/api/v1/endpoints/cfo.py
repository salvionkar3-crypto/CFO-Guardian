"""AI CFO Endpoints - Multi-Tenant Scoped

Every calculation and decision is strictly isolated to the caller's verified Business.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_business, get_current_user
from app.models.user import User
from app.models.business import Business, BusinessSettings
from app.models.vendor import Vendor
from app.models.payment import PaymentDraft
from app.models.audit import AuditLog
from app.schemas.cfo import CompanyMetrics, InvoiceAnalysisRequest, CFOAnalysisResult
from app.schemas.auth import BusinessSettingsSummary, BusinessSettingsUpdateRequest
from app.services.audit_service import AuditService
from app.core.config import settings

router = APIRouter()


@router.get("/metrics", response_model=CompanyMetrics)
def get_company_metrics(
    business: Business = Depends(get_current_business),
):
    """Retrieves business liquidity, budget utilization, and runway metrics for authenticated tenant."""
    budget_remaining = max(0.0, business.monthly_budget - business.monthly_spent)
    daily_burn = business.monthly_budget / 30.0 if business.monthly_budget > 0 else 1000.0
    runway_months = round(business.total_balance / business.monthly_budget, 1) if business.monthly_budget > 0 else 12.0

    return CompanyMetrics(
        name=business.name,
        operating_currency=business.currency,
        total_balance=business.total_balance,
        monthly_budget=business.monthly_budget,
        monthly_spent=business.monthly_spent,
        budget_remaining=budget_remaining,
        runway_months=runway_months,
        burn_rate_daily=round(daily_burn, 2),
    )


@router.post("/analyze", response_model=CFOAnalysisResult)
def analyze_invoice(
    request: InvoiceAnalysisRequest,
    business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ingests an expense invoice and calculates budget & runway impacts for the tenant."""
    daily_burn = business.monthly_budget / 30.0 if business.monthly_budget > 0 else 1000.0
    budget_impact_pct = round((request.amount / business.monthly_budget) * 100, 2) if business.monthly_budget > 0 else 0.0
    runway_impact_days = max(1, int(request.amount / daily_burn))

    remaining_budget = business.monthly_budget - business.monthly_spent

    # Retrieve or create vendor under this business tenant
    vendor = (
        db.query(Vendor)
        .filter(Vendor.business_id == business.id, Vendor.name == request.vendor)
        .first()
    )
    if not vendor:
        vendor = Vendor(
            business_id=business.id,
            name=request.vendor,
            email=request.vendor_email,
            bank_or_paypal_email=request.vendor_email,
            status="ACTIVE",
            trust_score=75.0,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

    # Apply CFO guardrails
    if request.amount > remaining_budget:
        recommendation = "REJECT"
        rationale = (
            f"Expense of ${request.amount:,.2f} exceeds remaining monthly budget "
            f"(${remaining_budget:,.2f}). Immediate executive review required to protect runway."
        )
        initial_status = "AWAITING_APPROVAL"
    elif request.amount > settings.AUTO_APPROVE_THRESHOLD_USD:
        recommendation = "FLAG_FOR_REVIEW"
        rationale = (
            f"Amount ${request.amount:,.2f} exceeds automatic approval ceiling "
            f"(${settings.AUTO_APPROVE_THRESHOLD_USD:.2f}). Consumes {budget_impact_pct}% of monthly budget "
            f"and represents {runway_impact_days} day(s) of operating burn."
        )
        initial_status = "AWAITING_APPROVAL"
    else:
        recommendation = "APPROVE"
        rationale = (
            f"Amount ${request.amount:,.2f} is within safe operational limits. "
            f"Consumes only {budget_impact_pct}% of monthly budget. Pre-approved pending Guardian AI security scan."
        )
        initial_status = "AWAITING_APPROVAL"

    draft = PaymentDraft(
        business_id=business.id,
        vendor_id=vendor.id,
        created_by_id=current_user.id,
        title=request.title,
        amount=request.amount,
        currency=request.currency or business.currency,
        category=request.category,
        purpose=request.notes or request.title,
        invoice_number=request.invoice_number,
        description=request.notes,
        status=initial_status,
        cfo_recommendation=recommendation,
        cfo_rationale=rationale,
        budget_impact_pct=budget_impact_pct,
        runway_impact_days=runway_impact_days,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    # Audit logs
    audit_understand = AuditLog(
        business_id=business.id,
        user_id=current_user.id,
        stage="UNDERSTAND",
        actor="AI_CFO",
        action="INGEST_INVOICE",
        summary=f"Ingested invoice from {request.vendor} for ${request.amount:,.2f} {request.currency}",
        details=f"Vendor: {request.vendor} ({request.vendor_email}), Draft #{draft.id}",
        rationale="Parsed invoice details and checked against company operational budget parameters.",
    )
    audit_analyze = AuditLog(
        business_id=business.id,
        user_id=current_user.id,
        stage="ANALYZE",
        actor="AI_CFO",
        action="EVALUATE_BUDGET_RUNWAY",
        summary=f"CFO Recommendation: {recommendation} (Budget Impact: {budget_impact_pct}%)",
        details=f"Draft #{draft.id} consumes {runway_impact_days} runway days.",
        rationale=rationale,
    )
    db.add_all([audit_understand, audit_analyze])
    db.commit()

    return CFOAnalysisResult(
        decision_id=draft.id,
        recommendation=draft.cfo_recommendation,
        rationale=draft.cfo_rationale or "",
        budget_impact_pct=draft.budget_impact_pct,
        runway_impact_days=draft.runway_impact_days,
        current_stage="ANALYZE",
    )


@router.get("/decisions")
def list_decisions(
    status: Optional[str] = Query(None, description="Filter by status (e.g. APPROVED, PENDING, PAID)"),
    limit: int = Query(25, ge=1, le=100),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Lists financial decisions strictly scoped to authenticated business tenant."""
    query = (
        db.query(PaymentDraft, Vendor)
        .join(Vendor, PaymentDraft.vendor_id == Vendor.id)
        .filter(PaymentDraft.business_id == business.id)
    )

    if status:
        query = query.filter(PaymentDraft.status == status.upper())

    records = query.order_by(PaymentDraft.created_at.desc()).limit(limit).all()

    results = []
    for draft, vendor in records:
        results.append({
            "id": draft.id,
            "title": draft.title,
            "vendor": vendor.name,
            "vendor_email": vendor.email,
            "category": draft.category,
            "amount": draft.amount,
            "currency": draft.currency,
            "status": draft.status,
            "cfo_recommendation": draft.cfo_recommendation,
            "cfo_rationale": draft.cfo_rationale,
            "budget_impact_pct": draft.budget_impact_pct,
            "runway_impact_days": draft.runway_impact_days,
            "current_stage": "DECIDE" if draft.status in ("APPROVED", "REJECTED") else "ANALYZE",
            "created_at": draft.created_at,
            "updated_at": draft.updated_at,
        })

    return results


@router.get("/settings", response_model=BusinessSettingsSummary)
def get_business_settings(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Retrieves business guardrail settings for authenticated tenant."""
    settings_obj = db.query(BusinessSettings).filter(BusinessSettings.business_id == business.id).first()
    if not settings_obj:
        settings_obj = BusinessSettings(business_id=business.id)
        db.add(settings_obj)
        db.commit()
        db.refresh(settings_obj)
    return BusinessSettingsSummary(
        id=settings_obj.id,
        auto_approve_threshold=settings_obj.auto_approve_threshold,
        max_single_payment_limit=settings_obj.max_single_payment_limit,
        require_dual_approval_above=settings_obj.require_dual_approval_above,
        risk_tolerance_level=settings_obj.risk_tolerance_level,
        approval_validity_hours=settings_obj.approval_validity_hours,
        block_critical_risk=settings_obj.block_critical_risk,
        notification_email=settings_obj.notification_email,
        enable_paypal_sandbox=settings_obj.enable_paypal_sandbox,
    )


@router.put("/settings", response_model=BusinessSettingsSummary)
@router.patch("/settings", response_model=BusinessSettingsSummary)
def update_business_settings(
    update_data: BusinessSettingsUpdateRequest,
    business: Business = Depends(get_current_business),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates business guardrail policies and logs CONFIGURATION_CHANGED to immutable audit ledger."""
    settings_obj = db.query(BusinessSettings).filter(BusinessSettings.business_id == business.id).first()
    if not settings_obj:
        settings_obj = BusinessSettings(business_id=business.id)
        db.add(settings_obj)
        db.commit()
        db.refresh(settings_obj)

    changes = []
    fields = [
        "auto_approve_threshold",
        "max_single_payment_limit",
        "require_dual_approval_above",
        "risk_tolerance_level",
        "approval_validity_hours",
        "block_critical_risk",
        "notification_email",
        "enable_paypal_sandbox",
    ]
    for field in fields:
        val = getattr(update_data, field)
        if val is not None:
            old_val = getattr(settings_obj, field)
            if old_val != val:
                setattr(settings_obj, field, val)
                changes.append(f"{field}: {old_val} -> {val}")

    if changes:
        db.commit()
        db.refresh(settings_obj)
        AuditService.log_event(
            db=db,
            business_id=business.id,
            user_id=user.id,
            stage="MONITOR",
            actor="USER",
            action="CONFIGURATION_CHANGED",
            summary=f"Business policy configuration updated by {user.full_name}",
            details="; ".join(changes),
            rationale="Updated treasury thresholds and risk policy guardrails.",
        )

    return BusinessSettingsSummary(
        id=settings_obj.id,
        auto_approve_threshold=settings_obj.auto_approve_threshold,
        max_single_payment_limit=settings_obj.max_single_payment_limit,
        require_dual_approval_above=settings_obj.require_dual_approval_above,
        risk_tolerance_level=settings_obj.risk_tolerance_level,
        approval_validity_hours=settings_obj.approval_validity_hours,
        block_critical_risk=settings_obj.block_critical_risk,
        notification_email=settings_obj.notification_email,
        enable_paypal_sandbox=settings_obj.enable_paypal_sandbox,
    )
