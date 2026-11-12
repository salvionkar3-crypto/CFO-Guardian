"""AI CFO Service

Analyzes business runway, cash flow impact, budget ceilings, and ROI.
Provides intelligent recommendations for expense approvals.
"""

from typing import Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.business import Business
from app.models.payment import PaymentDraft
from app.models.vendor import Vendor
from app.schemas.cfo import InvoiceAnalysisRequest
from app.services.audit_service import AuditService
from app.core.config import settings
from app.core.logging_config import logger


class CFOService:
    @staticmethod
    def get_or_create_company(db: Session) -> Business:
        """Retrieves default company profile or seeds one for demonstration."""
        business = db.query(Business).first()
        if not business:
            from app.db.seed import seed_demo_data
            seed_demo_data(db)
            business = db.query(Business).first()
        return business

    @staticmethod
    def calculate_runway_impact(company: Business, expense_amount: float) -> Tuple[float, int]:
        """Calculates budget consumption percentage and runway reduction in days."""
        daily_burn_rate = (company.monthly_budget / 30.0) if company.monthly_budget > 0 else 1000.0
        budget_impact_pct = round((expense_amount / company.monthly_budget) * 100, 2) if company.monthly_budget > 0 else 0.0
        runway_impact_days = int(expense_amount / daily_burn_rate) if daily_burn_rate > 0 else 1
        return budget_impact_pct, max(1, runway_impact_days)

    @classmethod
    def analyze_invoice(
        cls,
        db: Session,
        request: InvoiceAnalysisRequest,
    ) -> PaymentDraft:
        """Core AI CFO analysis workflow: Understand -> Analyze -> Decide."""
        company = cls.get_or_create_company(db)

        budget_impact_pct, runway_impact_days = cls.calculate_runway_impact(company, request.amount)

        # Decision heuristics
        is_within_auto_limit = request.amount <= settings.AUTO_APPROVE_THRESHOLD_USD
        remaining_budget = company.monthly_budget - company.monthly_spent

        if request.amount > remaining_budget:
            recommendation = "REJECT"
            rationale = (
                f"Expense of ${request.amount:,.2f} exceeds remaining monthly budget "
                f"(${remaining_budget:,.2f}). Immediate review required to prevent negative runway shock."
            )
            initial_status = "AWAITING_APPROVAL"
        elif not is_within_auto_limit:
            recommendation = "FLAG_FOR_REVIEW"
            rationale = (
                f"Amount ${request.amount:,.2f} exceeds the automatic approval limit "
                f"(${settings.AUTO_APPROVE_THRESHOLD_USD:.2f}). Consumes {budget_impact_pct}% of monthly budget "
                f"and represents {runway_impact_days} day(s) of operating runway."
            )
            initial_status = "AWAITING_APPROVAL"
        else:
            recommendation = "APPROVE"
            rationale = (
                f"Amount ${request.amount:,.2f} is within safe operational limits. "
                f"Consumes only {budget_impact_pct}% of monthly budget. Pre-approved pending Guardian AI security scan."
            )
            initial_status = "PENDING_INVESTIGATION"

        # Vendor resolution
        vendor = db.query(Vendor).filter(Vendor.business_id == company.id, Vendor.name == request.vendor).first()
        if not vendor:
            vendor = Vendor(
                business_id=company.id,
                name=request.vendor,
                email=request.vendor_email,
                bank_or_paypal_email=request.vendor_email,
                status="ACTIVE",
                trust_score=75.0,
            )
            db.add(vendor)
            db.commit()
            db.refresh(vendor)

        # Create PaymentDraft record
        decision = PaymentDraft(
            business_id=company.id,
            vendor_id=vendor.id,
            title=request.title,
            amount=request.amount,
            currency=request.currency,
            category=request.category,
            invoice_number=request.invoice_number,
            description=request.notes,
            status=initial_status,
            cfo_recommendation=recommendation,
            cfo_rationale=rationale,
            budget_impact_pct=budget_impact_pct,
            runway_impact_days=runway_impact_days,
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)

        # Audit logs for UNDERSTAND and ANALYZE
        AuditService.log_event(
            db=db,
            business_id=company.id,
            stage="UNDERSTAND",
            actor="AI_CFO",
            action="INGEST_INVOICE",
            summary=f"Ingested invoice from {request.vendor} for ${request.amount:,.2f} {request.currency}",
            decision_id=decision.id,
            details=f"Vendor: {request.vendor} ({request.vendor_email}), Category: {request.category}",
            rationale="Parsed invoice details and checked against company operational budget parameters.",
        )

        AuditService.log_event(
            db=db,
            business_id=company.id,
            stage="ANALYZE",
            actor="AI_CFO",
            action="EVALUATE_BUDGET_RUNWAY",
            summary=f"CFO Recommendation: {recommendation} (Budget Impact: {budget_impact_pct}%)",
            decision_id=decision.id,
            details=f"Runway impact: -{runway_impact_days} days. Remaining balance: ${company.total_balance:,.2f}",
            rationale=rationale,
        )

        return decision

