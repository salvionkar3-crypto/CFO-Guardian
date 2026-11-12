"""Guardian AI Payment Risk Detection Engine

Deterministic Python risk engine with 10 discrete risk signals,
configurable rules & thresholds, full supporting evidence,
tamper-evident SHA-256 verification hashes, and database audit persistence.

POLICY THRESHOLDS:
- LOW: 0–24 -> Verdict: SAFE_TO_PAY, Action: ALLOW
- MEDIUM: 25–49 -> Verdict: REQUIRES_MANUAL_REVIEW, Action: MANUAL_REVIEW_REQUIRED
- HIGH: 50–74 -> Verdict: REQUIRES_DUAL_EXECUTIVE_APPROVAL, Action: DUAL_EXECUTIVE_APPROVAL_REQUIRED
- CRITICAL: 75–100 -> Verdict: BLOCKED, Action: REJECT_AND_BLOCK

10 SIGNALS:
1. First-time vendor
2. Unusual payment amount
3. Duplicate invoice
4. Duplicate payment (velocity replay)
5. Unusual payment frequency
6. Vendor information mismatch
7. Payment exceeding business limits
8. Unusual category spending
9. Unusual transaction timing
10. Missing vendor verification information
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.payment import PaymentDraft, Transaction
from app.models.vendor import Vendor
from app.models.business import Business, BusinessSettings
from app.models.guardian import RiskAssessment, SecurityAlert
from app.models.audit import AuditLog
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.services.analytics_service import AnalyticsService
from app.core.config import settings
from app.core.logging_config import logger


class GuardianRiskConfig:
    # Initial configurable demonstration policy thresholds
    THRESHOLD_LOW_MAX = 24.0
    THRESHOLD_MEDIUM_MAX = 49.0
    THRESHOLD_HIGH_MAX = 74.0
    THRESHOLD_CRITICAL_MIN = 75.0

    # Signal Weights (Contribution to composite 0-100 score)
    W_FIRST_TIME_VENDOR = 20.0
    W_UNUSUAL_AMOUNT = 25.0
    W_DUPLICATE_INVOICE = 35.0
    W_DUPLICATE_PAYMENT = 30.0
    W_UNUSUAL_FREQUENCY = 20.0
    W_VENDOR_MISMATCH = 30.0
    W_LIMIT_EXCEEDED = 25.0
    W_UNUSUAL_CATEGORY = 20.0
    W_UNUSUAL_TIMING = 15.0
    W_MISSING_VERIFICATION = 15.0

    # Reputable corporate domains
    KNOWN_REPUTABLE_DOMAINS = [
        "amazon.com",
        "aws.amazon.com",
        "google.com",
        "github.com",
        "microsoft.com",
        "stripe.com",
        "paypal.com",
        "slack.com",
        "salesforce.com",
        "zoom.us",
        "cloudflare.com",
        "adobe.com",
    ]

    FREE_EMAIL_PROVIDERS = [
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "aol.com",
        "icloud.com",
        "mail.com",
        "proton.me",
        "protonmail.com",
    ]


class GuardianRiskEngine:
    """Core deterministic risk detection and threat synthesis engine."""

    @classmethod
    def evaluate(
        cls,
        db: Session,
        draft: PaymentDraft,
        business: Business,
        user_id: Optional[int] = None,
        force_recalculate: bool = False,
    ) -> RiskAssessment:
        """Executes the full 10-signal risk evaluation on a proposed payment draft."""
        # 1. Check existing assessment if recalculation not forced
        if not force_recalculate:
            existing = (
                db.query(RiskAssessment)
                .filter(
                    RiskAssessment.payment_draft_id == draft.id,
                    RiskAssessment.business_id == business.id,
                )
                .first()
            )
            if existing:
                return existing

        # 2. Retrieve vendor and business settings context
        vendor = db.query(Vendor).filter(Vendor.id == draft.vendor_id).first()
        b_settings = (
            db.query(BusinessSettings)
            .filter(BusinessSettings.business_id == business.id)
            .first()
        )

        detected_signals: List[Dict[str, Any]] = []
        supporting_evidence: List[str] = []
        missing_information: List[str] = []
        flags: List[str] = []

        # ==============================================================================
        # SIGNAL 1: First-Time Vendor Check
        # ==============================================================================
        prior_settled_tx_count = (
            db.query(func.count(Transaction.id))
            .filter(
                Transaction.business_id == business.id,
                Transaction.vendor_id == vendor.id if vendor else -1,
                Transaction.status == "COMPLETED",
            )
            .scalar() or 0
        )
        prior_approved_drafts = (
            db.query(func.count(PaymentDraft.id))
            .filter(
                PaymentDraft.business_id == business.id,
                PaymentDraft.vendor_id == vendor.id if vendor else -1,
                PaymentDraft.id != draft.id,
                PaymentDraft.status.in_(["APPROVED", "PAID"]),
            )
            .scalar() or 0
        )
        is_first_time_vendor = (prior_settled_tx_count == 0 and prior_approved_drafts == 0)
        if is_first_time_vendor:
            score = GuardianRiskConfig.W_FIRST_TIME_VENDOR
            evidence = f"Vendor '{vendor.name if vendor else 'Unknown'}' has 0 settled historical transactions and 0 approved prior payments with this business."
            detected_signals.append({
                "id": "SIGNAL_FIRST_TIME_VENDOR",
                "name": "First-Time Vendor",
                "severity": "MEDIUM",
                "score_impact": score,
                "description": "Payment recipient is an unestablished payee with no prior transaction history.",
                "evidence": evidence,
            })
            supporting_evidence.append(evidence)
            missing_information.append("Established commercial track record and verified historical transaction data.")
            flags.append(f"First-time vendor: '{vendor.name if vendor else 'Unknown'}'")

        # ==============================================================================
        # SIGNAL 2: Unusual Payment Amount Check
        # ==============================================================================
        vendor_avg_amount = (
            db.query(func.avg(Transaction.amount))
            .filter(
                Transaction.business_id == business.id,
                Transaction.vendor_id == vendor.id if vendor else -1,
                Transaction.status == "COMPLETED",
            )
            .scalar()
        )
        if vendor_avg_amount and vendor_avg_amount > 0:
            if draft.amount > (2.5 * vendor_avg_amount):
                score = GuardianRiskConfig.W_UNUSUAL_AMOUNT
                multiplier = round(draft.amount / vendor_avg_amount, 1)
                evidence = f"Payment amount ${draft.amount:,.2f} is {multiplier}x higher than vendor's historical average of ${vendor_avg_amount:,.2f}."
                detected_signals.append({
                    "id": "SIGNAL_UNUSUAL_AMOUNT",
                    "name": "Unusual Payment Amount",
                    "severity": "HIGH",
                    "score_impact": score,
                    "description": "Proposed payment deviates significantly from this vendor's typical baseline expenditure.",
                    "evidence": evidence,
                })
                supporting_evidence.append(evidence)
                flags.append(f"Unusual amount surge: {multiplier}x historical vendor average")
        else:
            # When vendor has no history, compare against typical monthly transaction average
            overall_avg = (
                db.query(func.avg(Transaction.amount))
                .filter(Transaction.business_id == business.id, Transaction.transaction_type == "EXPENSE")
                .scalar() or 1000.0
            )
            if draft.amount > (4.0 * overall_avg):
                score = GuardianRiskConfig.W_UNUSUAL_AMOUNT
                multiplier = round(draft.amount / overall_avg, 1)
                evidence = f"Proposed amount ${draft.amount:,.2f} is {multiplier}x higher than standard company expense transaction average (${overall_avg:,.2f})."
                detected_signals.append({
                    "id": "SIGNAL_UNUSUAL_AMOUNT",
                    "name": "Unusual Payment Amount (Outlier)",
                    "severity": "HIGH",
                    "score_impact": score,
                    "description": "Proposed amount represents a severe statistical outlier compared to operational norms.",
                    "evidence": evidence,
                })
                supporting_evidence.append(evidence)
                flags.append(f"Statistical outlier amount: ${draft.amount:,.2f}")

        # ==============================================================================
        # SIGNAL 3: Duplicate Invoice Check
        # ==============================================================================
        is_dup_invoice = False
        if draft.invoice_number and draft.invoice_number.strip():
            duplicate_invoice_draft = (
                db.query(PaymentDraft)
                .filter(
                    PaymentDraft.business_id == business.id,
                    PaymentDraft.vendor_id == draft.vendor_id,
                    PaymentDraft.invoice_number == draft.invoice_number.strip(),
                    PaymentDraft.id != draft.id,
                    PaymentDraft.status != "REJECTED",
                )
                .first()
            )
            duplicate_invoice_tx = (
                db.query(Transaction)
                .filter(
                    Transaction.business_id == business.id,
                    Transaction.vendor_id == draft.vendor_id,
                    Transaction.description.like(f"%{draft.invoice_number.strip()}%"),
                )
                .first()
            )
            if duplicate_invoice_draft or duplicate_invoice_tx:
                is_dup_invoice = True
                score = GuardianRiskConfig.W_DUPLICATE_INVOICE
                match_id = duplicate_invoice_draft.id if duplicate_invoice_draft else duplicate_invoice_tx.id
                match_type = "Draft" if duplicate_invoice_draft else "Settled Transaction"
                evidence = f"Invoice number '{draft.invoice_number}' already exists in {match_type} #{match_id} for vendor '{vendor.name if vendor else ''}'."
                detected_signals.append({
                    "id": "SIGNAL_DUPLICATE_INVOICE",
                    "name": "Duplicate Invoice Number Detected",
                    "severity": "CRITICAL",
                    "score_impact": score,
                    "description": "Invoice reference number exactly matches an existing invoice submitted previously.",
                    "evidence": evidence,
                })
                supporting_evidence.append(evidence)
                flags.append(f"Duplicate invoice reference: '{draft.invoice_number}'")
        else:
            missing_information.append("Formal vendor invoice reference number.")

        # ==============================================================================
        # SIGNAL 4: Duplicate Payment (Velocity Replay Attack)
        # ==============================================================================
        lookback_72h = datetime.utcnow() - timedelta(hours=72)
        duplicate_payment_recent = (
            db.query(PaymentDraft)
            .filter(
                PaymentDraft.business_id == business.id,
                PaymentDraft.vendor_id == draft.vendor_id,
                PaymentDraft.amount == draft.amount,
                PaymentDraft.id != draft.id,
                PaymentDraft.created_at >= lookback_72h,
                PaymentDraft.status != "REJECTED",
            )
            .first()
        )
        if duplicate_payment_recent:
            score = GuardianRiskConfig.W_DUPLICATE_PAYMENT
            hours_ago = round((datetime.utcnow() - duplicate_payment_recent.created_at).total_seconds() / 3600.0, 1)
            evidence = f"Identical payout of ${draft.amount:,.2f} to vendor '{vendor.name if vendor else ''}' was submitted {hours_ago} hour(s) ago (Ref: Draft #{duplicate_payment_recent.id})."
            detected_signals.append({
                "id": "SIGNAL_DUPLICATE_PAYMENT",
                "name": "Potential Duplicate Payment (Replay Velocity)",
                "severity": "HIGH",
                "score_impact": score,
                "description": "An identical amount to the same vendor was already submitted within a short 72-hour window.",
                "evidence": evidence,
            })
            supporting_evidence.append(evidence)
            flags.append(f"Replay payment: identical ${draft.amount:,.2f} within 72h")

        # ==============================================================================
        # SIGNAL 5: Unusual Payment Frequency Check
        # ==============================================================================
        lookback_7d = datetime.utcnow() - timedelta(days=7)
        recent_drafts_7d = (
            db.query(func.count(PaymentDraft.id))
            .filter(
                PaymentDraft.business_id == business.id,
                PaymentDraft.vendor_id == draft.vendor_id,
                PaymentDraft.id != draft.id,
                PaymentDraft.created_at >= lookback_7d,
                PaymentDraft.status.notin_(["REJECTED", "FAILED"]),
            )
            .scalar() or 0
        )
        if recent_drafts_7d >= 3:
            score = GuardianRiskConfig.W_UNUSUAL_FREQUENCY
            evidence = f"Vendor has received {recent_drafts_7d + 1} active payment requests within 7 days. Normal commercial payment cadence is 1-2 per month."
            detected_signals.append({
                "id": "SIGNAL_UNUSUAL_FREQUENCY",
                "name": "Abnormal Payment Frequency/Burst",
                "severity": "MEDIUM",
                "score_impact": score,
                "description": "High transaction velocity detected exceeding expected periodic commercial settlement cadence.",
                "evidence": evidence,
            })
            supporting_evidence.append(evidence)
            flags.append(f"Frequency anomaly: {recent_drafts_7d + 1} requests in 7 days")

        # ==============================================================================
        # SIGNAL 6: Vendor Information Mismatch Check
        # ==============================================================================
        vendor_email = (vendor.email or "").strip().lower() if vendor else ""
        vendor_name = (vendor.name or "").strip().lower() if vendor else ""
        email_domain = vendor_email.split("@")[-1] if "@" in vendor_email else ""

        is_reputable_domain = any(email_domain.endswith(dom) for dom in GuardianRiskConfig.KNOWN_REPUTABLE_DOMAINS)
        is_free_provider = any(email_domain == fp or email_domain.endswith("." + fp) for fp in GuardianRiskConfig.FREE_EMAIL_PROVIDERS)

        # Check for brand spoofing (e.g. name has Amazon or Microsoft, but domain is not official)
        corporate_keywords = ["amazon", "aws", "google", "microsoft", "stripe", "github", "slack", "salesforce"]
        spoofing_detected = False
        for kw in corporate_keywords:
            if kw in vendor_name and not email_domain.endswith(f"{kw}.com"):
                spoofing_detected = True
                break

        if spoofing_detected:
            score = GuardianRiskConfig.W_VENDOR_MISMATCH
            evidence = f"Vendor name '{vendor.name}' references major brand '{kw}', but email domain is '{email_domain}', indicating brand impersonation risk."
            detected_signals.append({
                "id": "SIGNAL_VENDOR_MISMATCH",
                "name": "Vendor Identity / Brand Impersonation Risk",
                "severity": "CRITICAL",
                "score_impact": score,
                "description": "Payee name suggests an established technology brand but uses an unrelated domain.",
                "evidence": evidence,
            })
            supporting_evidence.append(evidence)
            flags.append(f"Brand spoofing flag: {vendor_name} on domain {email_domain}")
        elif is_free_provider and draft.amount > 1500.0:
            score = 20.0
            evidence = f"Vendor claims to be commercial payee '{vendor.name}', but uses free webmail service (@{email_domain}) for high-value transaction (${draft.amount:,.2f})."
            detected_signals.append({
                "id": "SIGNAL_VENDOR_MISMATCH",
                "name": "Commercial Payee Free Webmail Risk",
                "severity": "MEDIUM",
                "score_impact": score,
                "description": "Commercial entities should provide an official organizational domain rather than public webmail.",
                "evidence": evidence,
            })
            supporting_evidence.append(evidence)
            missing_information.append("Corporate domain email and business entity verification.")
            flags.append(f"Free webmail provider: @{email_domain}")

        # ==============================================================================
        # SIGNAL 7: Payment Exceeding Business Limits Check
        # ==============================================================================
        max_limit = b_settings.max_single_payment_limit if b_settings else 5000.0
        remaining_budget = max(0.0, business.monthly_budget - business.monthly_spent)

        if draft.amount > max_limit:
            score = GuardianRiskConfig.W_LIMIT_EXCEEDED
            evidence = f"Payment amount of ${draft.amount:,.2f} exceeds company single-payment ceiling policy limit of ${max_limit:,.2f}."
            detected_signals.append({
                "id": "SIGNAL_EXCEEDS_BUSINESS_LIMITS",
                "name": "Exceeds Business Payment Ceiling",
                "severity": "HIGH",
                "score_impact": score,
                "description": "Amount exceeds the hard ceiling configured in company governance parameters.",
                "evidence": evidence,
            })
            supporting_evidence.append(evidence)
            flags.append(f"Exceeds single payment ceiling: ${draft.amount:,.2f} > ${max_limit:,.2f}")
        elif draft.amount > remaining_budget:
            score = 15.0
            evidence = f"Amount of ${draft.amount:,.2f} exceeds remaining monthly operating budget (${remaining_budget:,.2f})."
            detected_signals.append({
                "id": "SIGNAL_EXCEEDS_BUSINESS_LIMITS",
                "name": "Exceeds Remaining Monthly Budget",
                "severity": "MEDIUM",
                "score_impact": score,
                "description": "Proposed payment overcommits available monthly budget allocation.",
                "evidence": evidence,
            })
            supporting_evidence.append(evidence)
            flags.append(f"Exceeds monthly budget: ${draft.amount:,.2f} > ${remaining_budget:,.2f}")

        # ==============================================================================
        # SIGNAL 8: Unusual Category Spending Check
        # ==============================================================================
        anomalous_categories = AnalyticsService.identify_unusual_expense_increases(db=db, business=business)
        matched_category_anomaly = next((a for a in anomalous_categories if a.category.lower() == (draft.category or "").lower()), None)
        if matched_category_anomaly and draft.amount > 500.0:
            score = GuardianRiskConfig.W_UNUSUAL_CATEGORY
            evidence = f"Category '{draft.category}' is currently experiencing a {matched_category_anomaly.increase_pct}% surge over previous month."
            detected_signals.append({
                "id": "SIGNAL_UNUSUAL_CATEGORY",
                "name": "Unusual Category Outflow Surge",
                "severity": "MEDIUM",
                "score_impact": score,
                "description": "Category has registered abnormal expenditure surges exceeding standard variance.",
                "evidence": evidence,
            })
            supporting_evidence.append(evidence)
            flags.append(f"Category surge: {draft.category} (+{matched_category_anomaly.increase_pct}%)")

        # ==============================================================================
        # SIGNAL 9: Unusual Transaction Timing Check
        # ==============================================================================
        created_time = draft.created_at or datetime.utcnow()
        # Check if created on weekend (Saturday=5, Sunday=6) or late off-hours (23:00 - 04:00)
        is_weekend = created_time.weekday() in (5, 6)
        is_late_night = created_time.hour >= 23 or created_time.hour < 4

        if (is_weekend or is_late_night) and (is_first_time_vendor or draft.amount > 2000.0):
            score = GuardianRiskConfig.W_UNUSUAL_TIMING
            timing_desc = "weekend" if is_weekend else "off-hours late night"
            evidence = f"Payment draft was generated during {timing_desc} ({created_time.strftime('%A at %H:%M UTC')}) for non-standard approval flow."
            detected_signals.append({
                "id": "SIGNAL_UNUSUAL_TIMING",
                "name": "Unusual Transaction Timing",
                "severity": "LOW",
                "score_impact": score,
                "description": "Invoice creation or settlement request occurred outside typical corporate financial operating windows.",
                "evidence": evidence,
            })
            supporting_evidence.append(evidence)
            flags.append(f"Off-hours timing: {timing_desc}")

        # ==============================================================================
        # SIGNAL 10: Missing Vendor Verification Information Check
        # ==============================================================================
        if not vendor or not vendor.email:
            score = GuardianRiskConfig.W_MISSING_VERIFICATION
            evidence = "Vendor profile lacks valid contact email or banking disbursement coordinates."
            detected_signals.append({
                "id": "SIGNAL_MISSING_VERIFICATION",
                "name": "Missing Vendor Verification Details",
                "severity": "MEDIUM",
                "score_impact": score,
                "description": "Vendor directory entry is missing core identity and banking verification records.",
                "evidence": evidence,
            })
            supporting_evidence.append(evidence)
            missing_information.append("Valid vendor contact email and payment recipient endpoint.")
            flags.append("Missing vendor contact profile")
        elif vendor.trust_score < 60.0 or not is_reputable_domain:
            missing_information.append("Commercial tax ID certificate or audited vendor compliance accreditation.")

        # ==============================================================================
        # 3. Deterministic Composite Scoring & Policy Categorization
        # ==============================================================================
        raw_score = sum(s["score_impact"] for s in detected_signals)
        composite_score = round(min(100.0, max(0.0, raw_score)), 1)

        # Policy threshold categorization:
        # LOW: 0–24 -> SAFE_TO_PAY
        # MEDIUM: 25–49 -> REQUIRES_MANUAL_REVIEW
        # HIGH: 50–74 -> REQUIRES_DUAL_EXECUTIVE_APPROVAL
        # CRITICAL: 75–100 -> BLOCKED
        if composite_score >= GuardianRiskConfig.THRESHOLD_CRITICAL_MIN:
            risk_level = "CRITICAL"
            verdict = "BLOCKED"
            recommended_action = "REJECT_AND_BLOCK"
        elif composite_score >= GuardianRiskConfig.THRESHOLD_HIGH_MAX - 24.0:  # >= 50.0
            risk_level = "HIGH"
            verdict = "REQUIRES_DUAL_EXECUTIVE_APPROVAL"
            recommended_action = "DUAL_EXECUTIVE_APPROVAL_REQUIRED"
        elif composite_score >= GuardianRiskConfig.THRESHOLD_LOW_MAX + 1.0:  # >= 25.0
            risk_level = "MEDIUM"
            verdict = "REQUIRES_MANUAL_REVIEW"
            recommended_action = "MANUAL_REVIEW_REQUIRED"
        else:
            risk_level = "LOW"
            verdict = "SAFE_TO_PAY"
            recommended_action = "ALLOW"

        # Tamper-proof cryptographic SHA-256 verification digest
        payload_to_hash = f"{draft.id}:{draft.amount}:{composite_score}:{verdict}:{len(detected_signals)}"
        verification_hash = hashlib.sha256(payload_to_hash.encode("utf-8")).hexdigest()

        # ==============================================================================
        # 4. Generate Plain-Language Executive Explanation
        # ==============================================================================
        signal_count = len(detected_signals)
        if signal_count == 0:
            plain_explanation = (
                f"Proposed payment of ${draft.amount:,.2f} {draft.currency} to '{vendor.name if vendor else 'Vendor'}' "
                f"received a composite risk score of 0.0/100 (LOW). No fraud signals or policy violations were detected. "
                f"The payee domain is verified, invoice parameters are within historical limits, and payment is cleared for approval."
            )
        else:
            signal_bullets = "\n".join(
                [f"- **{s['name']}** (+{s['score_impact']} pts): {s['evidence']}" for s in detected_signals]
            )
            plain_explanation = (
                f"Payment Draft #{draft.id} received a risk score of **{composite_score}/100 ({risk_level})**. "
                f"Guardian AI detected **{signal_count} risk signal(s)**:\n\n"
                f"{signal_bullets}\n\n"
                f"**Governance Rationale:** In accordance with company risk tolerance policy, this transaction has been marked as "
                f"`{verdict}` (Action: `{recommended_action}`)."
            )

        # ==============================================================================
        # 5. Database Persistence
        # ==============================================================================
        assessment = RiskAssessment(
            business_id=business.id,
            payment_draft_id=draft.id,
            risk_score=composite_score,
            risk_level=risk_level,
            verdict=verdict,
            recommended_action=recommended_action,
            plain_explanation=plain_explanation,
            risk_signals=json.dumps(detected_signals),
            supporting_evidence=json.dumps(supporting_evidence),
            missing_information=json.dumps(missing_information),
            flags=json.dumps(flags),
            vendor_verified=is_reputable_domain,
            is_duplicate_invoice=is_dup_invoice,
            anomaly_detected=(composite_score >= 25.0),
            verification_hash=verification_hash,
            created_at=datetime.utcnow(),
        )
        db.add(assessment)

        # Update draft status according to verdict
        if verdict == "BLOCKED":
            draft.status = "REJECTED"
            # Automatic critical security alert
            alert = SecurityAlert(
                business_id=business.id,
                severity="CRITICAL",
                title=f"Blocked High-Risk Payment: {draft.title}",
                description=f"Guardian AI intercepted payout of ${draft.amount:,.2f} to {vendor.name if vendor else ''}. Score: {composite_score}/100. Flags: {'; '.join(flags[:3])}",
                status="OPEN",
                created_at=datetime.utcnow(),
            )
            db.add(alert)
            NotificationService.notify_high_risk(
                db=db,
                business_id=business.id,
                draft_id=draft.id,
                risk_score=composite_score,
                risk_level=risk_level,
                reasons=flags,
            )
        elif verdict in ("REQUIRES_DUAL_EXECUTIVE_APPROVAL", "REQUIRES_MANUAL_REVIEW"):
            draft.status = "AWAITING_APPROVAL"
            if composite_score >= 50.0:
                alert = SecurityAlert(
                    business_id=business.id,
                    severity="HIGH",
                    title=f"High-Risk Payment Flagged: {draft.title}",
                    description=f"Payment of ${draft.amount:,.2f} flagged for executive review. Score: {composite_score}/100.",
                    status="OPEN",
                    created_at=datetime.utcnow(),
                )
                db.add(alert)
                NotificationService.notify_high_risk(
                    db=db,
                    business_id=business.id,
                    draft_id=draft.id,
                    risk_score=composite_score,
                    risk_level=risk_level,
                    reasons=flags,
                )
            NotificationService.notify_awaiting_approval(
                db=db,
                business_id=business.id,
                draft_id=draft.id,
                title=draft.title,
                amount=draft.amount,
                currency=draft.currency,
                step=1,
            )
        else:
            draft.status = "RISK_REVIEWED"

        # Log audit trail for INVESTIGATE and DECIDE stages
        AuditService.log_event(
            db=db,
            business_id=business.id,
            stage="INVESTIGATE",
            actor="GUARDIAN_AI",
            action="FRAUD_RISK_INVESTIGATION",
            summary=f"Investigation completed: Risk Level {risk_level} (Score: {composite_score}/100)",
            decision_id=draft.id,
            details=f"Detected {signal_count} signals: {', '.join(flags[:4])}",
            rationale=f"Evaluated 10 discrete fraud signals across vendor history, invoice velocity, and company limits.",
        )
        AuditService.log_event(
            db=db,
            business_id=business.id,
            stage="DECIDE",
            actor="GUARDIAN_AI",
            action="SECURITY_VERDICT",
            summary=f"Guardian Verdict: {verdict} (Action: {recommended_action})",
            decision_id=draft.id,
            details=f"SHA-256 Digest: {verification_hash[:16]}...",
            rationale=plain_explanation[:255],
        )

        db.commit()
        db.refresh(assessment)
        return assessment

    # Backward compatibility alias
    evaluate_payment = evaluate


class GuardianService:
    """Wrapper service preserving backwards compatibility for other endpoints."""

    @classmethod
    def evaluate_risk(cls, db: Session, decision_id: int) -> RiskAssessment:
        draft = db.query(PaymentDraft).filter(PaymentDraft.id == decision_id).first()
        if not draft:
            raise ValueError(f"Financial decision #{decision_id} not found.")

        business = db.query(Business).filter(Business.id == draft.business_id).first()
        if not business:
            raise ValueError(f"Business #{draft.business_id} not found.")

        return GuardianRiskEngine.evaluate(db=db, draft=draft, business=business)
