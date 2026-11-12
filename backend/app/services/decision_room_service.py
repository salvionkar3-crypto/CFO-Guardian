"""Payment Decision Room Service

Compiles comprehensive, deterministic, multi-dimensional intelligence for high-stakes payment review:
1. Section A: Payment Overview
2. Section B: 10-Signal Intelligent Risk Assessment
3. Section C: Grounded AI Financial Recommendation (with deterministic fallback)
4. Section D: Precise Cash-Flow Impact Preview (Decimal-accurate arithmetic)
5. Section E: Human-Controlled Dual Authorization & Governance State
6. Section F: Immutable Payment Audit Timeline
7. PayPal REST Sandbox Status & Lifecycle Tracking
"""

import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import logger
from app.models.business import Business
from app.models.user import User
from app.models.vendor import Vendor
from app.models.payment import PaymentDraft, PaymentApproval, Transaction
from app.models.guardian import RiskAssessment
from app.models.audit import AuditLog
from app.services.guardian_service import GuardianRiskEngine
from app.services.policy_engine import PaymentPolicyEngine
from app.services.analytics_service import AnalyticsService
from app.services.paypal_service import PayPalService
from app.services.audit_service import AuditService
from app.schemas.payment import (
    PaymentDecisionRoomResponse,
    DecisionRoomOverview,
    DecisionRoomRiskSignal,
    DecisionRoomRiskAssessment,
    DecisionRoomAiRecommendation,
    DecisionRoomCommitmentItem,
    DecisionRoomCashFlowImpact,
    DecisionRoomApprover,
    DecisionRoomApprovalWorkflow,
    DecisionRoomAuditItem,
    DecisionRoomPayPalStatus,
)


class DecisionRoomService:
    """Orchestrates all intelligence layers for the Payment Decision Room."""

    @classmethod
    def get_decision_room_data(
        cls,
        db: Session,
        draft: PaymentDraft,
        business: Business,
        user: Optional[User] = None,
        force_recalculate_risk: bool = False,
    ) -> PaymentDecisionRoomResponse:
        """Assembles the complete Payment Decision Room payload for an active draft."""
        # Ensure latest expiration check is performed
        PaymentPolicyEngine.check_and_apply_expiration(db, draft, business)

        # ----------------------------------------------------------------------
        # 1. Section A: Payment Overview
        # ----------------------------------------------------------------------
        vendor = draft.vendor
        overview = DecisionRoomOverview(
            draft_id=draft.id,
            title=draft.title,
            vendor_id=draft.vendor_id,
            vendor_name=vendor.name if vendor else "Unknown Vendor",
            vendor_email=vendor.email if vendor else "",
            vendor_status=vendor.status if vendor else "UNVERIFIED",
            amount=round(draft.amount, 2),
            currency=draft.currency,
            invoice_number=draft.invoice_number,
            invoice_url=draft.invoice_url,
            purpose=draft.purpose or draft.description or "Operational disbursement",
            category=draft.category,
            status=draft.status,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
            details_hash=draft.details_hash,
            idempotency_key=draft.idempotency_key,
        )

        # ----------------------------------------------------------------------
        # 2. Section B: 10-Signal Intelligent Risk Assessment
        # ----------------------------------------------------------------------
        assessment = (
            db.query(RiskAssessment)
            .filter(RiskAssessment.payment_draft_id == draft.id, RiskAssessment.business_id == business.id)
            .order_by(RiskAssessment.created_at.desc())
            .first()
        )

        if not assessment or force_recalculate_risk:
            assessment = GuardianRiskEngine.evaluate(
                db=db,
                draft=draft,
                business=business,
                user_id=user.id if user else None,
                force_recalculate=True,
            )

        signals_raw = []
        if assessment.risk_signals:
            try:
                signals_raw = json.loads(assessment.risk_signals) if isinstance(assessment.risk_signals, str) else assessment.risk_signals
            except Exception:
                signals_raw = []

        signals_items: List[DecisionRoomRiskSignal] = []
        for s in signals_raw:
            signals_items.append(
                DecisionRoomRiskSignal(
                    id=s.get("id", "SIGNAL_ANOMALY"),
                    name=s.get("name", "Risk Signal"),
                    severity=s.get("severity", "MEDIUM"),
                    score_impact=float(s.get("score_impact", 0.0)),
                    description=s.get("description", ""),
                    evidence=s.get("evidence", ""),
                )
            )

        evidence_raw = []
        if assessment.supporting_evidence:
            try:
                evidence_raw = json.loads(assessment.supporting_evidence) if isinstance(assessment.supporting_evidence, str) else assessment.supporting_evidence
            except Exception:
                evidence_raw = []

        missing_raw = []
        if assessment.missing_information:
            try:
                missing_raw = json.loads(assessment.missing_information) if isinstance(assessment.missing_information, str) else assessment.missing_information
            except Exception:
                missing_raw = []

        flags_raw = []
        if assessment.flags:
            try:
                flags_raw = json.loads(assessment.flags) if isinstance(assessment.flags, str) else assessment.flags
            except Exception:
                flags_raw = []

        risk_data = DecisionRoomRiskAssessment(
            id=assessment.id,
            risk_score=round(assessment.risk_score, 1),
            risk_level=assessment.risk_level,
            verdict=assessment.verdict,
            recommended_action=assessment.recommended_action or "REQUIRES_MANUAL_REVIEW",
            plain_explanation=assessment.plain_explanation or f"Risk evaluated at {assessment.risk_score}/100 ({assessment.risk_level}).",
            signals=signals_items,
            supporting_evidence=[str(e) for e in evidence_raw],
            missing_information=[str(m) for m in missing_raw],
            flags=[str(f) for f in flags_raw],
            verification_hash=assessment.verification_hash,
            anomaly_detected=assessment.anomaly_detected,
            vendor_verified=assessment.vendor_verified,
            is_duplicate_invoice=assessment.is_duplicate_invoice,
            created_at=assessment.created_at.isoformat() if assessment.created_at else None,
        )

        # ----------------------------------------------------------------------
        # 3. Section D: Cash-Flow Impact Preview (Exact Decimal Arithmetic)
        # ----------------------------------------------------------------------
        amount_dec = Decimal(str(round(draft.amount, 2)))
        balance_dec = Decimal(str(round(business.total_balance, 2)))
        monthly_budget_dec = Decimal(str(round(business.monthly_budget, 2)))
        monthly_spent_dec = Decimal(str(round(business.monthly_spent, 2)))

        remaining_budget_before_dec = max(Decimal("0.00"), monthly_budget_dec - monthly_spent_dec)
        projected_cash_after_dec = balance_dec - amount_dec
        projected_monthly_spent_dec = monthly_spent_dec + amount_dec
        projected_remaining_budget_dec = max(Decimal("0.00"), monthly_budget_dec - projected_monthly_spent_dec)

        cash_consumed_pct = (
            round(float((amount_dec / balance_dec) * Decimal("100.0")), 2)
            if balance_dec > Decimal("0.00")
            else 0.0
        )
        budget_consumed_pct = (
            round(float((amount_dec / monthly_budget_dec) * Decimal("100.0")), 2)
            if monthly_budget_dec > Decimal("0.00")
            else 0.0
        )

        daily_burn_dec = (monthly_budget_dec / Decimal("30.0")) if monthly_budget_dec > Decimal("0.00") else Decimal("1000.00")
        runway_impact_days = max(1, int(amount_dec / daily_burn_dec))
        projected_runway_months = (
            round(float(projected_cash_after_dec / monthly_budget_dec), 1)
            if monthly_budget_dec > Decimal("0.00")
            else 0.0
        )

        # Retrieve verified recurring commitments
        commitments_data = AnalyticsService.identify_recurring_expenses(db=db, business=business)
        commitments_monthly_total = commitments_data.total_recurring_monthly
        active_commitments_count = len(commitments_data.items)

        commitments_sample = [
            DecisionRoomCommitmentItem(
                vendor_name=sub.vendor_name,
                category=sub.category,
                amount=sub.amount,
                frequency=sub.frequency,
            )
            for sub in commitments_data.items[:5]
        ]

        calc_notes = (
            f"Calculated against verified corporate treasury reserve of {business.currency} {float(balance_dec):,.2f}. "
            f"This single disbursement consumes {cash_consumed_pct:.2f}% of total available cash and represents "
            f"{runway_impact_days} operational burn day(s)."
        )

        cash_flow_impact = DecisionRoomCashFlowImpact(
            available_cash_before=float(balance_dec),
            payment_amount=float(amount_dec),
            projected_cash_after=float(projected_cash_after_dec),
            percentage_cash_consumed=cash_consumed_pct,
            monthly_budget=float(monthly_budget_dec),
            monthly_spent_before=float(monthly_spent_dec),
            projected_monthly_spent=float(projected_monthly_spent_dec),
            percentage_budget_consumed=budget_consumed_pct,
            remaining_budget_before=float(remaining_budget_before_dec),
            projected_remaining_budget=float(projected_remaining_budget_dec),
            runway_impact_days=runway_impact_days,
            projected_runway_months=projected_runway_months,
            commitments_monthly_total=commitments_monthly_total,
            active_commitments_count=active_commitments_count,
            commitments_sample=commitments_sample,
            calculation_notes=calc_notes,
        )

        # ----------------------------------------------------------------------
        # 4. Section C: AI Financial Recommendation (Grounded in Verified Telemetry)
        # ----------------------------------------------------------------------
        ai_recommendation = cls._build_ai_recommendation(
            draft=draft,
            business=business,
            vendor=vendor,
            risk_assessment=assessment,
            cash_flow=cash_flow_impact,
        )

        # ----------------------------------------------------------------------
        # 5. Section E: Human-Controlled Dual Authorization & Governance State
        # ----------------------------------------------------------------------
        eligibility = PaymentPolicyEngine.evaluate_approval_eligibility(db, draft, business, user=user)

        # Map approval history
        approvals_list: List[DecisionRoomApprover] = []
        if draft.approvals:
            for ap in sorted(draft.approvals, key=lambda x: x.approved_at or datetime.min):
                approver_name = ap.approved_by.full_name if ap.approved_by else "Executive Officer"
                approver_email = ap.approved_by.email if ap.approved_by else None
                approver_role = ap.approved_by.role if ap.approved_by else "OFFICER"
                approvals_list.append(
                    DecisionRoomApprover(
                        step=1 if ap.approval_role == "PRIMARY_APPROVER" else 2,
                        user_id=ap.approved_by_id,
                        name=approver_name,
                        email=approver_email,
                        role=approver_role,
                        approved_at=ap.approved_at,
                        notes=ap.notes,
                        details_hash=ap.details_hash,
                    )
                )

        primary_approver = approvals_list[0] if len(approvals_list) > 0 else None
        secondary_approver = approvals_list[1] if len(approvals_list) > 1 else None

        approval_workflow = DecisionRoomApprovalWorkflow(
            can_approve=eligibility.get("can_approve", False),
            mandatory_block=eligibility.get("mandatory_block", False),
            requires_dual_approval=eligibility.get("requires_dual_approval", False),
            current_step=eligibility.get("current_step", 1),
            total_steps=eligibility.get("total_steps", 1),
            step_name=eligibility.get("step_name", "APPROVAL_REVIEW"),
            reason=eligibility.get("reason", "Awaiting review."),
            recommended_action=eligibility.get("recommended_action", "MANUAL_REVIEW_REQUIRED"),
            primary_approver=primary_approver,
            secondary_approver=secondary_approver,
            approval_history=approvals_list,
            rejection_reason=draft.rejection_reason,
            details_hash=draft.details_hash,
            expires_at=draft.expires_at,
            is_expired=bool(draft.status == "EXPIRED"),
        )

        # ----------------------------------------------------------------------
        # 6. Section F: Immutable Payment Audit Timeline
        # ----------------------------------------------------------------------
        logs = (
            db.query(AuditLog)
            .filter(AuditLog.business_id == business.id, AuditLog.decision_id == draft.id)
            .order_by(AuditLog.created_at.asc())
            .all()
        )

        audit_timeline = [
            DecisionRoomAuditItem(
                id=log.id,
                stage=log.stage,
                actor=log.actor,
                action=log.action,
                summary=log.summary,
                details=log.details,
                rationale=log.rationale,
                timestamp=log.created_at,
            )
            for log in logs
        ]

        # ----------------------------------------------------------------------
        # 7. PayPal Sandbox Status & Lifecycle Tracking
        # ----------------------------------------------------------------------
        tx = (
            db.query(Transaction)
            .filter(Transaction.payment_draft_id == draft.id, Transaction.business_id == business.id)
            .order_by(Transaction.created_at.desc())
            .first()
        )

        is_paypal_configured = PayPalService.is_configured()
        masked_client_id = PayPalService.get_masked_client_id()

        approval_url = None
        if tx and tx.raw_paypal_response:
            try:
                raw_json = json.loads(tx.raw_paypal_response)
                approval_url = raw_json.get("approval_url")
            except Exception:
                approval_url = None

        paypal_status = DecisionRoomPayPalStatus(
            is_configured=is_paypal_configured,
            mode=settings.PAYPAL_MODE,
            client_id_preview=masked_client_id,
            order_id=tx.paypal_order_id if tx else None,
            capture_id=tx.paypal_capture_id if tx else None,
            approval_url=approval_url,
            transaction_status=tx.status if tx else ("NOT_INITIATED" if draft.status != "COMPLETED" else "COMPLETED"),
            settled_at=tx.settled_at if tx else None,
        )

        return PaymentDecisionRoomResponse(
            overview=overview,
            risk_assessment=risk_data,
            ai_recommendation=ai_recommendation,
            cash_flow_impact=cash_flow_impact,
            approval_workflow=approval_workflow,
            audit_timeline=audit_timeline,
            paypal_status=paypal_status,
        )

    @classmethod
    def _build_ai_recommendation(
        cls,
        draft: PaymentDraft,
        business: Business,
        vendor: Optional[Vendor],
        risk_assessment: RiskAssessment,
        cash_flow: DecisionRoomCashFlowImpact,
    ) -> DecisionRoomAiRecommendation:
        """Grounded synthesis answering the 5 mandatory CFO review questions."""
        # 1. Collect Verified Facts
        facts = [
            f"Corporate cash reserves before payout: {business.currency} {cash_flow.available_cash_before:,.2f}",
            f"Monthly operational budget: {business.currency} {cash_flow.monthly_budget:,.2f} ({business.currency} {cash_flow.remaining_budget_before:,.2f} remaining)",
            f"Payee '{vendor.name if vendor else 'Unknown'}' has {vendor.total_paid if vendor else 0.0:,.2f} {business.currency} historical settled payouts",
            f"Proposed disbursement consumes {cash_flow.percentage_cash_consumed:.1f}% of total cash reserves and {cash_flow.percentage_budget_consumed:.1f}% of monthly budget",
            f"Reduces operational runway by {cash_flow.runway_impact_days} day(s), leaving {cash_flow.projected_runway_months:.1f} months of projected runway",
        ]

        # 2. Why Risky
        if risk_assessment.risk_score >= 75.0:
            why_risky = (
                f"CRITICAL RISK ({risk_assessment.risk_score}/100): High likelihood of capital loss or policy circumvention. "
                f"Triggered critical signals: {', '.join(risk_assessment.flags) if risk_assessment.flags else 'Anomalous payment patterns'}."
            )
        elif risk_assessment.risk_score >= 50.0:
            why_risky = (
                f"HIGH RISK ({risk_assessment.risk_score}/100): Triggers mandatory dual executive authorization. "
                f"Significant variance from vendor baseline and single-payment ceiling policies."
            )
        elif risk_assessment.risk_score >= 25.0:
            why_risky = (
                f"MODERATE RISK ({risk_assessment.risk_score}/100): Minor anomalies or first-time commercial relationship detected. "
                f"Review required to verify vendor deliverable."
            )
        else:
            why_risky = (
                f"LOW RISK ({risk_assessment.risk_score}/100): Safe transaction within established operational parameters. "
                f"Vendor is verified and disbursement aligns with routine recurring schedule."
            )

        # 3. Cash Flow Impact
        if cash_flow.payment_amount > cash_flow.available_cash_before:
            cf_impact = f"CRITICAL: Proposed payout exceeds total company liquidity ({business.currency} {cash_flow.available_cash_before:,.2f}). Immediate overdraft/insolvency risk."
        elif cash_flow.payment_amount > cash_flow.remaining_budget_before:
            cf_impact = (
                f"BUDGET DEFICIT: Payment exceeds remaining monthly budget by "
                f"{business.currency} {(cash_flow.payment_amount - cash_flow.remaining_budget_before):,.2f}. "
                f"Consumes {cash_flow.runway_impact_days} days of operational burn."
            )
        else:
            cf_impact = (
                f"SUSTAINABLE: Payment is comfortably covered by operating reserves. "
                f"Post-payment balance will be {business.currency} {cash_flow.projected_cash_after:,.2f} "
                f"with {cash_flow.projected_runway_months} months runway."
            )

        # 4. Required Verifications
        verifications = []
        if not risk_assessment.vendor_verified:
            verifications.append("Verify corporate registration and official corporate domain email with payee.")
        if cash_flow.percentage_budget_consumed > 10.0:
            verifications.append("Obtain written countersignature from Department Budget Owner for spend exceeding 10% of monthly allocation.")
        if risk_assessment.risk_score >= 50.0:
            verifications.append("Enforce Four-Eyes Principle: Secondary authorization required from a distinct corporate officer.")
        if not draft.invoice_number:
            verifications.append("Require vendor tax invoice reference before final settlement dispatch.")
        if not verifications:
            verifications.append("Standard verification complete. Verify invoice goods/services receipt prior to PayPal order dispatch.")

        # 5. Suggested Action
        if risk_assessment.risk_score >= 75.0 or draft.amount > cash_flow.available_cash_before:
            suggested_action = "REJECT_AND_BLOCK: Do not authorize. Request formal supplier re-verification or reject invoice."
        elif risk_assessment.risk_score >= 50.0 or draft.amount > 1000.0:
            suggested_action = "DUAL_APPROVAL_REQUIRED: Primary officer should record review notes, then invite secondary executive to co-authorize."
        elif risk_assessment.risk_score >= 25.0:
            suggested_action = "REQUEST_REVIEW: Confirm scope of deliverables with project lead before granting single approval."
        else:
            suggested_action = "APPROVE: Ready for executive authorization and PayPal Sandbox settlement."

        return DecisionRoomAiRecommendation(
            why_risky=why_risky,
            verified_facts=facts,
            cash_flow_impact=cf_impact,
            required_verifications=verifications,
            recommended_reviewer_action=suggested_action,
            is_ai_generated=False,
            disclaimer=(
                "Deterministic Zero-Hallucination Recommendation: Synthesized directly from verified corporate database telemetry. "
                "AI recommendations are strictly advisory; financial disbursement requires human executive authorization."
            ),
        )

    @classmethod
    def ensure_demo_scenario(
        cls,
        db: Session,
        business: Business,
        user: User,
        scenario_key: str,
    ) -> PaymentDraft:
        """Ensures the exact Hackathon demonstration scenarios exist and are evaluated by the real risk engine."""
        scenario_key = scenario_key.lower().strip()

        if scenario_key == "normal":
            # Scenario 1: Normal Payment to Datadog Cloud Observability ($280.00 USD)
            vendor_name = "Datadog Cloud Observability"
            vendor_email = "billing@datadoghq.com"
            amount = 280.00
            purpose = "Monthly infrastructure monitoring"
            title = "Datadog Cloud APM & Infrastructure Observability"
            category = "Infrastructure"
            invoice_num = "INV-DDOG-2026-M11"

            vendor = db.query(Vendor).filter(Vendor.business_id == business.id, Vendor.name == vendor_name).first()
            if not vendor:
                vendor = Vendor(
                    business_id=business.id,
                    name=vendor_name,
                    email=vendor_email,
                    bank_or_paypal_email=vendor_email,
                    status="ACTIVE",
                    trust_score=88.0,
                    website="https://www.datadoghq.com",
                    total_paid=1120.00,
                )
                db.add(vendor)
                db.commit()
                db.refresh(vendor)

            draft = (
                db.query(PaymentDraft)
                .filter(
                    PaymentDraft.business_id == business.id,
                    PaymentDraft.vendor_id == vendor.id,
                    PaymentDraft.title == title,
                )
                .order_by(PaymentDraft.id.desc())
                .first()
            )

            if not draft:
                draft = PaymentDraft(
                    business_id=business.id,
                    vendor_id=vendor.id,
                    created_by_id=user.id,
                    title=title,
                    amount=amount,
                    currency="USD",
                    category=category,
                    purpose=purpose,
                    invoice_number=invoice_num,
                    description="Monthly production tracing and anomaly detection",
                    status="AWAITING_APPROVAL",
                    cfo_recommendation="APPROVE",
                    cfo_rationale="Expense of $280.00 represents 0.8% of monthly budget. Standard recurring utility.",
                    budget_impact_pct=0.8,
                    runway_impact_days=1,
                    created_at=datetime.utcnow() - timedelta(minutes=45),
                )
                db.add(draft)
                db.commit()
                db.refresh(draft)

                # Evaluate with real Guardian AI Risk Engine
                GuardianRiskEngine.evaluate(db=db, draft=draft, business=business, user_id=user.id, force_recalculate=True)

                AuditService.log_event(
                    db=db,
                    business_id=business.id,
                    user_id=user.id,
                    stage="UNDERSTAND",
                    actor="AI_CFO",
                    action="CREATE_PAYMENT_DRAFT",
                    summary=f"Created Payment Draft #{draft.id} for USD 280.00 to {vendor.name}",
                    details="Scenario 1: Normal operational utility payment for Datadog.",
                    rationale="Routine recurring expenditure within safe operational envelope.",
                    decision_id=draft.id,
                )

            return draft

        elif scenario_key == "suspicious":
            # Scenario 2: Suspicious Payment to Global Offshore FinTech Direct Ltd ($25,000.00 USD)
            vendor_name = "Global Offshore FinTech Direct Ltd"
            vendor_email = "wire-transfer@offshore-pay-express88.xyz"
            amount = 25000.00
            purpose = "Urgent advisory fee"
            title = "Urgent International Cross-Border Retainer"
            category = "Consulting"
            invoice_num = "INV-OFFSHORE-9912"

            vendor = db.query(Vendor).filter(Vendor.business_id == business.id, Vendor.name == vendor_name).first()
            if not vendor:
                vendor = Vendor(
                    business_id=business.id,
                    name=vendor_name,
                    email=vendor_email,
                    bank_or_paypal_email=vendor_email,
                    status="UNVERIFIED",
                    trust_score=15.0,
                    website="http://offshore-pay-express88.xyz",
                    total_paid=0.00,
                )
                db.add(vendor)
                db.commit()
                db.refresh(vendor)

            draft = (
                db.query(PaymentDraft)
                .filter(
                    PaymentDraft.business_id == business.id,
                    PaymentDraft.vendor_id == vendor.id,
                    PaymentDraft.title == title,
                )
                .order_by(PaymentDraft.id.desc())
                .first()
            )

            if not draft:
                draft = PaymentDraft(
                    business_id=business.id,
                    vendor_id=vendor.id,
                    created_by_id=user.id,
                    title=title,
                    amount=amount,
                    currency="USD",
                    category=category,
                    purpose=purpose,
                    invoice_number=invoice_num,
                    description="Urgent retainer requested prior to contract countersignature",
                    status="AWAITING_APPROVAL",
                    cfo_recommendation="FLAG_FOR_REVIEW",
                    cfo_rationale="Expense of $25,000.00 exceeds single payment ceiling ($5,000) and triggers high-risk fraud heuristics.",
                    budget_impact_pct=71.4,
                    runway_impact_days=25,
                    created_at=datetime.utcnow() - timedelta(minutes=20),
                )
                db.add(draft)
                db.commit()
                db.refresh(draft)

                # Real risk engine evaluation
                GuardianRiskEngine.evaluate(db=db, draft=draft, business=business, user_id=user.id, force_recalculate=True)

                AuditService.log_event(
                    db=db,
                    business_id=business.id,
                    user_id=user.id,
                    stage="UNDERSTAND",
                    actor="AI_CFO",
                    action="CREATE_PAYMENT_DRAFT",
                    summary=f"Created Payment Draft #{draft.id} for USD 25,000.00 to {vendor.name}",
                    details="Scenario 2: Suspicious large offshore advisory payment.",
                    rationale="Evaluated against strict 10-signal fraud engine and payment ceilings.",
                    decision_id=draft.id,
                )

            return draft

        else:
            raise ValueError(f"Unknown demo scenario key: '{scenario_key}'. Expected 'normal' or 'suspicious'.")
